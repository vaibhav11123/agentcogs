import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import orjson
from fastapi import APIRouter, Depends, HTTPException, Request

from ..deps import rate_limit_ingest
from ..models import CostEventIn, IngestBatchIn
from ..services.admission import month_key, settle
from ..services.anomaly import check_anomaly
from ..tasks import spawn
from agentcogs.kernel import allocate_case
from app.kernel.cusum import cusum_signals

router = APIRouter()
log = logging.getLogger("agentcogs.ingest")
_fault_commits = 0
_customer_ids: dict[tuple[str, str], str] = {}
_books: dict[str, tuple[str, dict]] = {}
_seen_workspaces: set[str] = set()

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


async def _customer_id(db, workspace_id, external_id: str) -> str:
    key = (str(workspace_id), external_id)
    found = _customer_ids.get(key)
    if found is not None:
        return found
    cust_id = await db.fetchval(
        """
        INSERT INTO customers (workspace_id, external_id, display_name)
        VALUES ($1, $2, $2)
        ON CONFLICT (workspace_id, external_id) DO NOTHING
        RETURNING id
        """,
        workspace_id,
        external_id,
    )
    if cust_id is None:
        cust_id = await db.fetchval(
            "SELECT id FROM customers WHERE workspace_id = $1 AND external_id = $2",
            workspace_id,
            external_id,
        )
    if cust_id is None:
        raise HTTPException(422, detail="CUSTOMER_UNRESOLVED")
    _customer_ids[key] = str(cust_id)
    return _customer_ids[key]


async def _touch_workspace(db, workspace_id) -> None:
    key = str(workspace_id)
    if key in _seen_workspaces:
        return
    await db.execute(
        """
        UPDATE workspaces
        SET sdk_first_seen_at = COALESCE(sdk_first_seen_at, NOW()),
            first_cost_event_at = COALESCE(first_cost_event_at, NOW())
        WHERE id = $1
        """,
        workspace_id,
    )
    _seen_workspaces.add(key)


async def _load_book(db, book_id: str | None) -> tuple[str, dict]:
    if book_id and book_id in _books:
        return _books[book_id]
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
    loaded = row["book_id"], {"usd_per_million": rates, "lanes": lanes, "reasoning_lane": "reasoning"}
    _books[str(loaded[0])] = loaded
    return loaded


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


def _fault_after_commit() -> None:
    """Test hook. Exit after the database commit and before Redis settlement."""
    fault = os.environ.get("AGENTCOGS_FAULT", "")
    if fault != "after_commit":
        return
    global _fault_commits
    _fault_commits += 1
    target = int(os.environ.get("AGENTCOGS_FAULT_AFTER", "1"))
    if _fault_commits >= target:
        log.error("fault after_commit: exiting before settlement")
        os._exit(86)


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
    cust_id = await _customer_id(db, ws["id"], event.customer_id)
    ts = datetime.fromtimestamp(event.ts, tz=timezone.utc)
    priced = None
    book_id = None
    price_error = None
    total_micro = usd_to_micro(event.total_usd)
    stored_usd = event.total_usd
    if event.calls:
        book_id, book = await _load_book(db, event.book_id)
        try:
            priced = _price(event, book)
            total_micro = sum(int(v) for v in priced["incurred_micro"].values())
            if abs(usd_to_micro(event.total_usd) - total_micro) > 1:
                price_error = "PRICE_MISMATCH"
            else:
                stored_usd = Decimal(total_micro) / Decimal(1_000_000)
        except ValueError as exc:
            price_error = str(exc)

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

    calls_out = _plain_calls(event.calls or []) if priced is not None else []
    if priced is not None:
        for call in calls_out:
            call["incurred_micro"] = int(priced["incurred_micro"][call["call_id"]])
    async with db.acquire() as conn:
        async with conn.transaction():
            already = await conn.fetchval(
                "SELECT 1 FROM cost_events WHERE workspace_id = $1 AND id = $2",
                ws["id"],
                event.run_id,
            )
            if already or price_error:
                inserted = None
            else:
                inserted = await conn.fetchval(insert_sql, *insert_args)
            if inserted and priced is not None:
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
                line_args: list = []
                placeholders: list[str] = []
                index = 1
                for call_id, micro in priced["allocated_micro"].items():
                    placeholders.append(
                        f"(${index},${index + 1},${index + 2},'allocated',${index + 3},${index + 4},${index + 5})"
                    )
                    line_args.extend([ws["id"], pane, event.run_id, call_id, int(micro), ts])
                    index += 6
                if placeholders:
                    await conn.execute(
                        f"""
                        INSERT INTO allocation_lines
                          (workspace_id, pane_id, run_id, segment_id, call_id, micro, event_time)
                        VALUES {",".join(placeholders)}
                        """,
                        *line_args,
                    )
    if already or not inserted:
        if not already and price_error:
            raise HTTPException(422, detail=price_error)
        return await _on_duplicate(db, redis, ws["id"], cust_id, event, ts, total_micro)

    _fault_after_commit()

    await _touch_workspace(db, ws["id"])

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


@router.post("/v1/ingest/batch", status_code=202)
async def ingest_batch(
    body: IngestBatchIn,
    request: Request,
    ws: dict = Depends(rate_limit_ingest),
):
    """One transaction for the runs in this request. Each run keeps its own result."""
    db = request.app.state.db
    redis = request.app.state.redis
    prepared = []
    for event in body.events:
        cust_id = await _customer_id(db, ws["id"], event.customer_id)
        ts = datetime.fromtimestamp(event.ts, tz=timezone.utc)
        priced = None
        book_id = None
        price_error = None
        total_micro = usd_to_micro(event.total_usd)
        stored_usd = event.total_usd
        if event.calls:
            book_id, book = await _load_book(db, event.book_id)
            try:
                priced = _price(event, book)
                total_micro = sum(int(v) for v in priced["incurred_micro"].values())
                if abs(usd_to_micro(event.total_usd) - total_micro) > 1:
                    price_error = "PRICE_MISMATCH"
                else:
                    stored_usd = Decimal(total_micro) / Decimal(1_000_000)
            except ValueError as exc:
                price_error = str(exc)
        prepared.append(
            {
                "event": event,
                "cust_id": cust_id,
                "ts": ts,
                "priced": priced,
                "book_id": book_id,
                "price_error": price_error,
                "total_micro": total_micro,
                "stored_usd": stored_usd,
            }
        )

    results: dict[str, dict] = {}
    inserted_rows = []
    async with db.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetch(
                "SELECT id::text AS id FROM cost_events WHERE workspace_id = $1 AND id = ANY($2::uuid[])",
                ws["id"],
                [item["event"].run_id for item in prepared],
            )
            existing_ids = {row["id"] for row in existing}
            fresh = []
            for item in prepared:
                run_id = item["event"].run_id
                if run_id in existing_ids or item["price_error"]:
                    results[run_id] = {"existing": run_id in existing_ids, "price_error": item["price_error"]}
                    continue
                fresh.append(item)
            if fresh:
                values = []
                args: list = []
                index = 1
                for item in fresh:
                    event = item["event"]
                    values.append(
                        f"(${index}::uuid,${index + 1},${index + 2},${index + 3},${index + 4},${index + 5},"
                        f"${index + 6},${index + 7}::jsonb,${index + 8}::jsonb,${index + 9}::jsonb,${index + 10})"
                    )
                    args.extend(
                        [
                            event.run_id,
                            ws["id"],
                            item["cust_id"],
                            event.workflow_id,
                            item["ts"],
                            event.status,
                            item["stored_usd"],
                            _serialize_models(event.models),
                            _serialize_dict(event.node_costs),
                            _serialize_dict(event.metadata),
                            event.error,
                        ]
                    )
                    index += 11
                stored = await conn.fetch(
                    f"""
                    INSERT INTO cost_events
                      (id, workspace_id, customer_id, workflow_id, ts, status,
                       total_usd, model_breakdown, node_breakdown, metadata, error)
                    VALUES {",".join(values)}
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id::text AS id
                    """,
                    *args,
                )
                stored_ids = {row["id"] for row in stored}
                fact_values = []
                fact_args: list = []
                line_values = []
                line_args: list = []
                receipt_values = []
                receipt_args: list = []
                fi = li = ri = 1
                for item in fresh:
                    event = item["event"]
                    if event.run_id not in stored_ids:
                        results[event.run_id] = {"existing": True, "price_error": None}
                        continue
                    inserted_rows.append(item)
                    month = datetime(item["ts"].year, item["ts"].month, 1, tzinfo=timezone.utc).date()
                    receipt_values.append(f"(${ri},${ri + 1},${ri + 2},${ri + 3},${ri + 4})")
                    receipt_args.extend([ws["id"], event.run_id, item["cust_id"], month, item["total_micro"]])
                    ri += 5
                    if item["priced"] is None:
                        continue
                    calls_out = _plain_calls(event.calls or [])
                    for call in calls_out:
                        call["incurred_micro"] = int(item["priced"]["incurred_micro"][call["call_id"]])
                    fact_values.append(
                        f"(${fi},${fi + 1},${fi + 2},${fi + 3},${fi + 4},${fi + 5},${fi + 6},${fi + 7}::jsonb,${fi + 8}::jsonb,${fi + 9}::jsonb)"
                    )
                    fact_args.extend(
                        [
                            ws["id"],
                            event.run_id,
                            item["cust_id"],
                            item["ts"],
                            item["book_id"],
                            item["total_micro"],
                            item["priced"]["mode"],
                            _jsonb({"wire_micro": usd_to_micro(event.total_usd)}),
                            _jsonb(calls_out),
                            _jsonb(_plain_segments(event.segments)),
                        ]
                    )
                    fi += 10
                    pane = f"run:{event.run_id}:0"
                    for call_id, micro in item["priced"]["allocated_micro"].items():
                        line_values.append(
                            f"(${li},${li + 1},${li + 2},'allocated',${li + 3},${li + 4},${li + 5})"
                        )
                        line_args.extend([ws["id"], pane, event.run_id, call_id, int(micro), item["ts"]])
                        li += 6
                if fact_values:
                    await conn.execute(
                        f"""
                        INSERT INTO ledger_facts
                          (workspace_id, run_id, customer_id, event_time, book_id,
                           incurred_micro, allocation_mode, lanes, calls, segments)
                        VALUES {",".join(fact_values)}
                        """,
                        *fact_args,
                    )
                if line_values:
                    await conn.execute(
                        f"""
                        INSERT INTO allocation_lines
                          (workspace_id, pane_id, run_id, segment_id, call_id, micro, event_time)
                        VALUES {",".join(line_values)}
                        """,
                        *line_args,
                    )
                if receipt_values:
                    await conn.execute(
                        f"""
                        INSERT INTO settlement_receipts
                          (workspace_id, run_id, customer_id, month, actual_micro)
                        VALUES {",".join(receipt_values)}
                        ON CONFLICT (workspace_id, run_id) DO NOTHING
                        """,
                        *receipt_args,
                    )

    _fault_after_commit()
    await _touch_workspace(db, ws["id"])
    out = []
    for item in prepared:
        event = item["event"]
        run_id = event.run_id
        state = results.get(run_id)
        if item in inserted_rows:
            try:
                await settle(redis, str(ws["id"]), str(item["cust_id"]), run_id, int(item["total_micro"]), month=month_key(item["ts"]))
            except Exception:
                log.exception("batch settle failed")
            out.append({"accepted": True, "run_id": run_id})
            continue
        if state and state["existing"]:
            try:
                dup = await _on_duplicate(db, redis, ws["id"], item["cust_id"], event, item["ts"], item["total_micro"])
            except HTTPException as exc:
                out.append({"accepted": False, "run_id": run_id, "status": exc.status_code, "detail": exc.detail})
                continue
            out.append({**dup, "run_id": run_id})
            continue
        out.append({"accepted": False, "run_id": run_id, "status": 422, "detail": state["price_error"] if state else "REJECTED"})
    return {"results": out}


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
    stored_customer = await db.fetchval(
        "SELECT customer_id FROM cost_events WHERE workspace_id = $1 AND id = $2",
        workspace_id,
        event.run_id,
    )
    if stored_customer is not None:
        customer_id = stored_customer
    try:
        await _settle_receipt(db, redis, workspace_id, customer_id, event.run_id, total_micro, ts)
    except Exception:
        log.exception("duplicate settle failed")
    return {"accepted": True, "duplicate": True, "run_id": event.run_id}


def _serialize_models(models: dict) -> str:
    return orjson.dumps({k: v.model_dump() for k, v in models.items()}).decode()


def _serialize_dict(d: dict) -> str:
    return orjson.dumps(d).decode()
