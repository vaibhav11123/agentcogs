"""Generate synthetic cost events that look like real LangGraph traffic."""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import httpx

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from personas import ALL_PERSONAS, PERSONAS, Persona  # noqa: E402


def _weighted_choice(d: dict[str, float]) -> str:
    keys, weights = zip(*d.items())
    return random.choices(keys, weights=weights, k=1)[0]


def _gauss_positive(mean: float, stddev: float, min_value: float = 0.0) -> float:
    return max(min_value, random.gauss(mean, stddev))


def _build_model_breakdown(persona: Persona, total_cost: float) -> dict:
    model = _weighted_choice(persona.models)
    in_tokens = int(
        _gauss_positive(persona.avg_input_tokens, persona.avg_input_tokens * 0.3, 50)
    )
    out_tokens = int(
        _gauss_positive(persona.avg_output_tokens, persona.avg_output_tokens * 0.3, 20)
    )

    if "claude" in model:
        cache_pct = random.uniform(0.0, 0.7)
        cache_read = int(in_tokens * cache_pct)
        non_cached = in_tokens - cache_read
        return {
            model: {
                "input_tokens": non_cached,
                "output_tokens": out_tokens,
                "usd": round(total_cost, 6),
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": 0,
            }
        }

    return {
        model: {
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "usd": round(total_cost, 6),
        }
    }


def _build_node_breakdown(workflow: str, total_cost: float) -> dict[str, float]:
    node_templates = {
        "summarize": ["chunk", "summarize", "merge"],
        "extract": ["parse", "extract", "validate"],
        "classify": ["classify"],
        "research_agent": ["plan", "search", "synthesize", "critique"],
        "deep_analysis": ["outline", "gather", "analyze", "draft", "review"],
        "contract_review": ["parse", "clause_extract", "compare", "summarize"],
        "compliance_check": ["scan", "rule_match", "report"],
    }
    nodes = node_templates.get(workflow, ["main"])
    weights = [random.random() for _ in nodes]
    total_w = sum(weights)
    return {n: round(total_cost * w / total_w, 6) for n, w in zip(nodes, weights)}


def generate_run(
    persona: Persona,
    ts: datetime,
    *,
    is_anomaly: bool = False,
    workflow: str | None = None,
    cost_override: float | None = None,
) -> dict:
    wf = workflow or _weighted_choice(persona.workflows)

    if cost_override is not None:
        cost = cost_override
        is_anomaly = is_anomaly or cost > persona.cost_per_run_mean * 3
    elif is_anomaly:
        multiplier = random.uniform(5.0, 20.0)
        cost = persona.cost_per_run_mean * multiplier
    else:
        cost = _gauss_positive(
            persona.cost_per_run_mean,
            persona.cost_per_run_stddev,
            min_value=0.0001,
        )

    return {
        "run_id": str(uuid.uuid4()),
        "workspace_id": "WORKSPACE_OVERRIDE",
        "customer_id": persona.external_id,
        "workflow_id": wf,
        "ts": int(ts.timestamp()),
        "status": "completed",
        "total_usd": round(cost, 6),
        "models": _build_model_breakdown(persona, cost),
        "node_costs": _build_node_breakdown(wf, cost),
        "metadata": {"synthetic": True, "anomaly": is_anomaly},
    }


def iter_events_for_persona(
    persona: Persona,
    start: datetime,
    end: datetime,
) -> Iterator[dict]:
    quiet_cutoff = end - timedelta(days=persona.quiet_days_end) if persona.quiet_days_end else None
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < end:
        if quiet_cutoff and day >= quiet_cutoff.replace(hour=0, minute=0, second=0, microsecond=0):
            day += timedelta(days=1)
            continue

        run_count = max(
            0,
            int(_gauss_positive(persona.runs_per_day_mean, persona.runs_per_day_stddev)),
        )
        anomaly_day = random.random() < persona.anomaly_rate

        for _ in range(run_count):
            hour = int(random.triangular(0, 23, mode=13))
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            ts = day.replace(hour=hour, minute=minute, second=second)
            if ts < start or ts > end:
                continue
            is_spike = anomaly_day and random.random() < 0.05
            yield generate_run(persona, ts, is_anomaly=is_spike)

        day += timedelta(days=1)


def _persona_by_id(external_id: str) -> Persona:
    return next(p for p in ALL_PERSONAS if p.external_id == external_id)


def month_start_utc(dt: datetime) -> datetime:
    """Match backend leaderboard_query: UTC calendar month start."""
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def mtd_cost_for_persona(events: list[dict], external_id: str, end: datetime) -> float:
    ms_ts = int(month_start_utc(end).timestamp())
    end_ts = int(end.timestamp())
    return sum(
        e["total_usd"]
        for e in events
        if e["customer_id"] == external_id and ms_ts <= e["ts"] <= end_ts
    )


def apply_mtd_calibration(events: list[dict], end: datetime) -> list[dict]:
    """Top up current-month spend so MTD margins match persona targets (dashboard math)."""
    extra: list[dict] = []
    month_start = month_start_utc(end)

    for persona in ALL_PERSONAS:
        if persona.target_margin_pct is None or persona.monthly_revenue_usd <= 0:
            continue

        target_cost = persona.monthly_revenue_usd * (1 - persona.target_margin_pct / 100)
        current = mtd_cost_for_persona(events + extra, persona.external_id, end)
        delta = target_cost - current
        if delta <= 0.01:
            continue

        n_runs = max(4, min(40, int(delta / max(persona.cost_per_run_mean, 0.01))))
        per_run = delta / n_runs
        days_in_month = max((end.date() - month_start.date()).days, 1)

        for i in range(n_runs):
            day = month_start + timedelta(days=i % days_in_month)
            hour = int(random.triangular(8, 20, 14))
            ts = day.replace(
                hour=hour,
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )
            if ts > end:
                ts = end - timedelta(minutes=random.randint(15, 180))
            extra.append(generate_run(persona, ts, cost_override=round(per_run, 6)))

    return sorted(events + extra, key=lambda x: x["ts"])


def apply_narrative_events(events: list[dict], end: datetime) -> list[dict]:
    """Buried demo stories: TechFlow mid-month spike, Initech recent anomaly."""
    extra: list[dict] = []

    techflow = _persona_by_id("techflow_inc")
    for days_ago in (15, 16, 17):
        spike_day = (end - timedelta(days=days_ago)).replace(hour=14, minute=30, second=0)
        for _ in range(8):
            ts = spike_day.replace(minute=random.randint(0, 59))
            extra.append(
                generate_run(
                    techflow,
                    ts,
                    workflow="research_agent",
                    cost_override=techflow.cost_per_run_mean * random.uniform(1.8, 2.4),
                )
            )

    initech = _persona_by_id("initech")
    anomaly_ts = end - timedelta(hours=random.randint(6, 48))
    extra.append(
        generate_run(
            initech,
            anomaly_ts,
            workflow="research_agent",
            is_anomaly=True,
            cost_override=initech.cost_per_run_mean * random.uniform(18, 22),
        )
    )

    return sorted(events + extra, key=lambda x: x["ts"])


def collect_all_events(start: datetime, end: datetime) -> list[dict]:
    all_events: list[dict] = []
    for persona in ALL_PERSONAS:
        all_events.extend(iter_events_for_persona(persona, start, end))
    all_events = apply_narrative_events(all_events, end)
    return apply_mtd_calibration(all_events, end)


def iter_all_events(start: datetime, end: datetime) -> Iterator[dict]:
    for event in collect_all_events(start, end):
        yield event


async def post_to_backend(
    events: Iterator[dict],
    *,
    endpoint: str,
    api_key: str,
    workspace_id: str,
    rate_limit: float = 50.0,
) -> tuple[int, int]:
    sent = failed = 0
    delay = 1.0 / rate_limit
    async with httpx.AsyncClient(
        base_url=endpoint.rstrip("/"),
        timeout=10,
        headers={"Authorization": f"Bearer {api_key}"},
    ) as client:
        for ev in events:
            ev["workspace_id"] = workspace_id
            try:
                r = await client.post("/v1/ingest", json=ev)
                if r.status_code == 202:
                    sent += 1
                else:
                    failed += 1
                    print(f"⚠️ {r.status_code}: {r.text[:200]}", file=sys.stderr)
            except Exception as e:
                failed += 1
                print(f"⚠️ error: {e}", file=sys.stderr)
            if sent % 100 == 0 and sent > 0:
                print(f"  sent={sent} failed={failed}", file=sys.stderr)
            await asyncio.sleep(delay)
    return sent, failed


def dump_to_jsonl(events: Iterator[dict], path: str) -> int:
    count = 0
    with open(path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")
            count += 1
    return count


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate synthetic AgentCOGS events")
    ap.add_argument("--days", type=int, default=30, help="Days of history to generate")
    ap.add_argument("--mode", choices=["post", "file"], default="file")
    ap.add_argument("--endpoint", default="http://localhost:8000")
    ap.add_argument("--api-key", default="acg_live_TEST_E2E_KEY_DO_NOT_USE_IN_PROD")
    ap.add_argument("--workspace-id", default="")
    ap.add_argument("--output", default="events.jsonl", help="JSONL output path")
    ap.add_argument("--rate", type=float, default=50.0, help="Events/sec for post mode")
    ap.add_argument("--seed", type=int, default=42, help="Reproducible seed")
    args = ap.parse_args()

    random.seed(args.seed)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    print(
        f"Generating {args.days} days of events for {len(ALL_PERSONAS)} personas...",
        file=sys.stderr,
    )

    events = collect_all_events(start, end)
    print(f"Generated {len(events):,} events", file=sys.stderr)

    if args.mode == "file":
        count = dump_to_jsonl(iter(events), args.output)
        print(f"Wrote {count:,} events → {args.output}", file=sys.stderr)
    else:
        if not args.workspace_id:
            ap.error("--workspace-id required for post mode")
        sent, failed = asyncio.run(
            post_to_backend(
                iter(events),
                endpoint=args.endpoint,
                api_key=args.api_key,
                workspace_id=args.workspace_id,
                rate_limit=args.rate,
            )
        )
        print(f"✅ done: sent={sent} failed={failed}", file=sys.stderr)


if __name__ == "__main__":
    main()
