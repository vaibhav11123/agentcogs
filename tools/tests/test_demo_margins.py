"""Validate demo persona margins against call-script targets (offline simulation)."""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_TOOLS))

from generate_events import collect_all_events, mtd_cost_for_persona  # noqa: E402
from personas import ALL_PERSONAS, HERO_PERSONAS  # noqa: E402

MARGIN_TOLERANCE = 8.0  # points — gaussian variance on MTD window


def _margin_pct(revenue: float, cost: float) -> float:
    if revenue <= 0:
        return 0.0
    return (revenue - cost) / revenue * 100


def _hero_mtd_margins(end: datetime) -> dict[str, float]:
    start = end - timedelta(days=30)
    events = collect_all_events(start, end)
    margins: dict[str, float] = {}
    for p in HERO_PERSONAS:
        if p.monthly_revenue_usd <= 0:
            continue
        cost = mtd_cost_for_persona(events, p.external_id, end)
        margins[p.external_id] = _margin_pct(p.monthly_revenue_usd, cost)
    return margins


def test_persona_roster_size():
    assert len(ALL_PERSONAS) == 40
    assert len(HERO_PERSONAS) == 7


def test_hero_margin_bands():
    random.seed(42)
    end = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    margins = _hero_mtd_margins(end)

    for p in HERO_PERSONAS:
        if p.target_margin_pct is None or p.monthly_revenue_usd <= 0:
            continue
        margin = margins[p.external_id]
        assert abs(margin - p.target_margin_pct) <= MARGIN_TOLERANCE, (
            f"{p.external_id}: MTD margin {margin:.1f}% vs target {p.target_margin_pct}%"
        )


def test_acme_healthier_than_techflow():
    random.seed(42)
    end = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    margins = _hero_mtd_margins(end)
    acme_m = margins["acme_corp"]
    tech_m = margins["techflow_inc"]
    assert acme_m > tech_m + 20, f"Acme {acme_m:.1f}% should beat TechFlow {tech_m:.1f}% by 20+ pts"


def test_hooli_quiet_period():
    random.seed(42)
    end = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=30)
    recent_cutoff = int((end - timedelta(days=14)).timestamp())
    recent = [
        ev
        for ev in collect_all_events(start, end)
        if ev["customer_id"] == "hooli" and ev["ts"] >= recent_cutoff
    ]
    assert len(recent) == 0, "Hooli should have no runs in last 14 days (churning)"


def test_narrative_initech_anomaly():
    random.seed(42)
    end = datetime(2026, 5, 19, 12, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=30)
    big = [
        ev
        for ev in collect_all_events(start, end)
        if ev["customer_id"] == "initech" and ev["total_usd"] > 5.0
    ]
    assert len(big) >= 1, "Initech should have at least one $5+ anomaly event"
