import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from ..deps import enforce_plan_limits
from ..models import CostEventIn
from ..services.anomaly import check_anomaly

router = APIRouter()


@router.post("/v1/ingest", status_code=202)
async def ingest(
    event: CostEventIn,
    request: Request,
    ws: dict = Depends(enforce_plan_limits),
):
    db = request.app.state.db
    redis = request.app.state.redis

    # 1. Upsert customer.
    cust_id = await db.fetchval(
        """
        INSERT INTO customers (workspace_id, external_id, display_name)
        VALUES ($1, $2, $2)
        ON CONFLICT (workspace_id, external_id)
        DO UPDATE SET external_id = EXCLUDED.external_id
        RETURNING id
        """,
        ws["id"],
        event.customer_id,
    )

    ts = datetime.fromtimestamp(event.ts, tz=timezone.utc)

    # 2. Idempotent insert (run_id = PK).
    inserted = await db.fetchval(
        """
        INSERT INTO cost_events
          (id, workspace_id, customer_id, workflow_id, ts, status,
           total_usd, model_breakdown, node_breakdown, metadata, error)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10::jsonb,$11)
        ON CONFLICT (id) DO NOTHING
        RETURNING id
        """,
        event.run_id,
        ws["id"],
        cust_id,
        event.workflow_id,
        ts,
        event.status,
        event.total_usd,
        _serialize_models(event.models),
        _serialize_dict(event.node_costs),
        _serialize_dict(event.metadata),
        event.error,
    )

    if not inserted:
        # Duplicate — early return, no counter increment.
        return {"accepted": True, "duplicate": True, "run_id": event.run_id}

    # 3. Redis: increment monthly+daily counters in one pipeline.
    month = ts.strftime("%Y-%m")
    day = ts.strftime("%Y-%m-%d")
    month_key = f"spend:ws_{ws['id']}:cust_{cust_id}:{month}"
    day_key = f"spend:ws_{ws['id']}:cust_{cust_id}:{day}"

    async with redis.pipeline(transaction=False) as pipe:
        pipe.hincrbyfloat(month_key, "usd", event.total_usd)
        pipe.hincrby(month_key, "count", 1)
        pipe.expire(month_key, 86400 * 90)
        pipe.hincrbyfloat(day_key, "usd", event.total_usd)
        pipe.expire(day_key, 86400 * 35)
        await pipe.execute()

    # 4. Trigger anomaly check (non-blocking).
    asyncio.create_task(
        check_anomaly(
            db,
            redis,
            workspace_id=ws["id"],
            cost_event_id=event.run_id,
            customer_id=cust_id,
            workflow_id=event.workflow_id,
            current_usd=event.total_usd,
        )
    )

    return {"accepted": True, "run_id": event.run_id}


def _serialize_models(models: dict) -> str:
    import orjson

    return orjson.dumps({k: v.model_dump() for k, v in models.items()}).decode()


def _serialize_dict(d: dict) -> str:
    import orjson

    return orjson.dumps(d).decode()
