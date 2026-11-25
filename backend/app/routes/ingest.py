import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import orjson
from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import rate_limit_ingest
from ..models import CostEventIn
from ..services.admission import month_key, settle
from ..services.anomaly import check_anomaly
from ..tasks import spawn
from agentcogs.kernel import allocate_case
from app.kernel.cusum import cusum_signals

router = APIRouter()
log = logging.getLogger("agentcogs.ingest")

_INPUT_LANES = (
    "uncached_input",
    "cache_read",
    "cache_write_5m",
    "cache_write_1h",
    "cache_write_30m",
    "cache_write_12h",
)


def usd_to_micro(value) -> int:
    quant = Decimal(str(value)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return int(quant * Decimal(1_000_000))


def money_fingerprint(total_micro: int, calls, segments) -> str:
    if calls is None:
        payload = {"total_micro": int(total_micro)}
    else:
        payload = {
            "total_micro": int(total_micro),
            "calls": calls,
            "segments": segments or [],
        }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _plain_calls(calls) -> list[dict]:
    plain = []
    for call in calls:
        data = call.model_dump() if hasattr(call, "model_dump") else dict(call)
        data.pop("incurred_micro", None)
        plain.append(data)
    return plain


def _plain_segments(segments) -> list[dict]:
    if not segments:
        return []
    return [segment.model_dump() if hasattr(segment, "model_dump") else dict(segment) for segment in segments]


def _jsonb(value) -> str:
    return orjson.dumps(value).decode()


async def _load_book(db, book_id: str | None) -> tuple[str, dict]:
    if book_id:
        row = await db.fetchrow(
            "SELECT book_id, usd_per_million, lanes FROM price_books WHERE book_id = $1",
            book_id,
        )
    else:
        row = await db.fetchrow(
            "SELECT book_id, usd_per_million, lanes FROM price_books ORDER BY created_at DESC LIMIT 1"
        )
    if not row:
        raise HTTPException(422, detail="PRICE_MISMATCH")
    rates = row["usd_per_million"]
    lanes = row["lanes"]
    if isinstance(rates, str):
        rates = json.loads(rates)
    if isinstance(lanes, str):
        lanes = json.loads(lanes)
    return row["book_id"], {"usd_per_million": rates, "lanes": lanes, "reasoning_lane": "reasoning"}


def _price(event: CostEventIn, book: dict) -> dict:
    calls = _plain_calls(event.calls or [])
    for call in calls:
        declared = call.get("provider_input_tokens")
        if declared is None:
            continue
        total = sum(int(call["lanes"].get(name, 0) or 0) for name in _INPUT_LANES)
        if total != int(declared):
            raise ValueError("LANE_MISMATCH")
    case = {"calls": calls, "segments": _plain_segments(event.segments)}
    try:
        return allocate_case(case, book)
    except ValueError:
        raise
    except KeyError as exc:
        raise ValueError("LANE_MISMATCH") from exc


async def _settle_receipt(db, redis, workspace_id, customer_id, run_id, actual_micro, when: datetime) -> None:
    month = month_key(when)
    await settle(redis, str(workspace_id), str(customer_id), str(run_id), int(actual_micro), month=month)
    await db.execute(
        """
        INSERT INTO settlement_receipts
          (workspace_id, run_id, customer_id, month, actual_micro)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (workspace_id, run_id) DO NOTHING
        """,
        workspace_id,
        run_id,
        customer_id,
        datetime(when.year, when.month, 1, tzinfo=timezone.utc).date(),
        int(actual_micro),
    )


async def check_cusum(db, *, workspace_id, customer_id, cost_event_id) -> None:
    try:
        rows = await db.fetch(
            """
            SELECT (al.event_time AT TIME ZONE 'UTC')::date AS day,
                   SUM(al.micro)::bigint AS micro
            FROM allocation_lines al
            JOIN ledger_facts f
              ON f.workspace_id = al.workspace_id AND f.run_id = al.run_id
            WHERE f.workspace_id = $1
              AND f.customer_id = $2
              AND al.event_time > NOW() - INTERVAL '45 days'
            GROUP BY 1
            ORDER BY 1
            """,
            workspace_id,
            customer_id,
        )
        series = [(row["day"].weekday(), int(row["micro"])) for row in rows]
        if sum(1 for _, micro in series if micro > 0) < 30:
            return
        if not cusum_signals(series):
            return
        already = await db.fetchval(
            """
            SELECT 1 FROM anomalies
            WHERE workspace_id = $1 AND customer_id = $2 AND detector = 'cusum'
              AND (created_at AT TIME ZONE 'UTC')::date = (NOW() AT TIME ZONE 'UTC')::date
            """,
            workspace_id,
            customer_id,
        )
        if already:
            return
        await db.execute(
            """
            INSERT INTO anomalies
              (workspace_id, cost_event_id, customer_id, z_score, multiplier, mean_usd, detector)
            VALUES ($1, $2, $3, NULL, NULL, NULL, 'cusum')
            """,
            workspace_id,
            cost_event_id,
            customer_id,
        )
    except Exception:
        log.exception("cusum check failed")


@router.post("/v1/ingest", status_code=202)
async def ingest(
    event: CostEventIn,
    request: Request,
    ws: dict = Depends(rate_limit_ingest),
):
    db = request.app.state.db
    redis = request.app.state.redis
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
    already = await db.fetchval(
        "SELECT 1 FROM cost_events WHERE workspace_id = $1 AND id = $2",
        ws["id"],
        event.run_id,
    )
    if already:
        return await _on_duplicate(db, redis, ws["id"], cust_id, event, ts, usd_to_micro(event.total_usd))

    priced = None
    book_id = None
    if event.calls:
        book_id, book = await _load_book(db, event.book_id)
        try:
            priced = _price(event, book)
        except ValueError as exc:
            raise HTTPException(422, detail=str(exc)) from exc
        total_micro = sum(int(v) for v in priced["incurred_micro"].values())
        if abs(usd_to_micro(event.total_usd) - total_micro) > 1:
            raise HTTPException(422, detail="PRICE_MISMATCH")
        stored_usd = Decimal(total_micro) / Decimal(1_000_000)
    else:
        total_micro = usd_to_micro(event.total_usd)
        stored_usd = event.total_usd

    insert_sql = """
        INSERT INTO cost_events
          (id, workspace_id, customer_id, workflow_id, ts, status,
           total_usd, model_breakdown, node_breakdown, metadata, error)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10::jsonb,$11)
        ON CONFLICT (id) DO NOTHING
        RETURNING id
        """
    insert_args = (
        event.run_id,
        ws["id"],
        cust_id,
        event.workflow_id,
        ts,
        event.status,
        stored_usd,
        _serialize_models(event.models),
        _serialize_dict(event.node_costs),
        _serialize_dict(event.metadata),
        event.error,
    )

    if priced is None:
        inserted = await db.fetchval(insert_sql, *insert_args)
        if not inserted:
            return await _on_duplicate(db, redis, ws["id"], cust_id, event, ts, total_micro)
    else:
        calls_out = _plain_calls(event.calls or [])
        for call in calls_out:
            call["incurred_micro"] = int(priced["incurred_micro"][call["call_id"]])
        async with db.acquire() as conn:
            async with conn.transaction():
                inserted = await conn.fetchval(insert_sql, *insert_args)
                if inserted:
                    await conn.execute(
                        """
                        INSERT INTO ledger_facts
                          (workspace_id, run_id, customer_id, event_time, book_id,
                           incurred_micro, allocation_mode, lanes, calls, segments)
                        VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10::jsonb)
                        """,
                        ws["id"],
                        event.run_id,
                        cust_id,
                        ts,
                        book_id,
                        total_micro,
                        priced["mode"],
                        _jsonb({"wire_micro": usd_to_micro(event.total_usd)}),
                        _jsonb(calls_out),
                        _jsonb(_plain_segments(event.segments)),
                    )
                    pane = f"run:{event.run_id}:0"
                    for call_id, micro in priced["allocated_micro"].items():
                        await conn.execute(
                            """
                            INSERT INTO allocation_lines
                              (workspace_id, pane_id, run_id, segment_id, call_id, micro, event_time)
                            VALUES ($1,$2,$3,'allocated',$4,$5,$6)
                            """,
                            ws["id"],
                            pane,
                            event.run_id,
                            call_id,
                            int(micro),
                            ts,
                        )
        if not inserted:
            return await _on_duplicate(db, redis, ws["id"], cust_id, event, ts, total_micro)

    await db.execute(
        """
        UPDATE workspaces
        SET sdk_first_seen_at = COALESCE(sdk_first_seen_at, NOW()),
            first_cost_event_at = COALESCE(first_cost_event_at, NOW())
        WHERE id = $1
        """,
        ws["id"],
    )

    month = ts.strftime("%Y-%m")
    day = ts.strftime("%Y-%m-%d")
    month_spend = f"spend:ws_{ws['id']}:cust_{cust_id}:{month}"
    day_spend = f"spend:ws_{ws['id']}:cust_{cust_id}:{day}"
    async with redis.pipeline(transaction=False) as pipe:
        pipe.hincrbyfloat(month_spend, "usd", float(stored_usd))
        pipe.hincrby(month_spend, "count", 1)
        pipe.expire(month_spend, 86400 * 90)
        pipe.hincrbyfloat(day_spend, "usd", float(stored_usd))
        pipe.expire(day_spend, 86400 * 35)
        await pipe.execute()

    try:
        await _settle_receipt(db, redis, ws["id"], cust_id, event.run_id, total_micro, ts)
    except Exception:
        log.exception("settle failed after commit")

    spawn(
        check_anomaly(
            db,
            redis,
            workspace_id=ws["id"],
            cost_event_id=event.run_id,
            customer_id=cust_id,
            workflow_id=event.workflow_id or "default",
            current_usd=float(stored_usd),
        )
    )
    if priced is not None:
        spawn(check_cusum(db, workspace_id=ws["id"], customer_id=cust_id, cost_event_id=event.run_id))

    return {"accepted": True, "run_id": event.run_id}


async def _on_duplicate(db, redis, workspace_id, customer_id, event: CostEventIn, ts: datetime, total_micro: int):
    fact = await db.fetchrow(
        """
        SELECT incurred_micro, calls, segments, lanes
        FROM ledger_facts
        WHERE workspace_id = $1 AND run_id = $2
        """,
        workspace_id,
        event.run_id,
    )
    if fact is None:
        if event.calls:
            raise HTTPException(409, detail="PAYLOAD_MISMATCH")
        stored = await db.fetchrow(
            "SELECT total_usd FROM cost_events WHERE workspace_id = $1 AND id = $2",
            workspace_id,
            event.run_id,
        )
        if stored is not None and usd_to_micro(stored["total_usd"]) != usd_to_micro(event.total_usd):
            raise HTTPException(409, detail="PAYLOAD_MISMATCH")
    else:
        stored_calls = fact["calls"]
        if isinstance(stored_calls, str):
            stored_calls = json.loads(stored_calls)
        stored_segments = fact["segments"]
        if isinstance(stored_segments, str):
            stored_segments = json.loads(stored_segments)
        stored_lanes = fact["lanes"] if "lanes" in fact else {}
        cleaned = []
        for call in stored_calls or []:
            item = dict(call)
            item.pop("incurred_micro", None)
            cleaned.append(item)
        if isinstance(stored_lanes, str):
            stored_lanes = json.loads(stored_lanes)
        wire = int((stored_lanes or {}).get("wire_micro", fact["incurred_micro"]))
        current = money_fingerprint(
            usd_to_micro(event.total_usd),
            _plain_calls(event.calls) if event.calls else None,
            _plain_segments(event.segments) if event.calls else None,
        )
        previous = money_fingerprint(wire, cleaned if event.calls else None, stored_segments if event.calls else None)
        if current != previous:
            raise HTTPException(409, detail="PAYLOAD_MISMATCH")
        total_micro = int(fact["incurred_micro"])
    try:
        await _settle_receipt(db, redis, workspace_id, customer_id, event.run_id, total_micro, ts)
    except Exception:
        log.exception("duplicate settle failed")
    return {"accepted": True, "duplicate": True, "run_id": event.run_id}


def _serialize_models(models: dict) -> str:
    return orjson.dumps({k: v.model_dump() for k, v in models.items()}).decode()


def _serialize_dict(d: dict) -> str:
    return orjson.dumps(d).decode()
