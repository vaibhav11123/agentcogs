"""Deterministic filler customers — brings demo roster to ~40 tenants."""
from __future__ import annotations

import random

from personas import Persona

_FILLER_SPECS: list[tuple[str, str, str, float, float, float, float]] = [
    # display_name, external_id, archetype, revenue, target_margin_pct, runs/day, budget
    ("Folio Health", "folio_health", "healthy", 2400, 72, 45, 180),
    ("Stackline", "stackline_io", "healthy", 1800, 68, 35, 150),
    ("Meridian Labs", "meridian_labs", "healthy", 3200, 74, 55, 220),
    ("Northwind AI", "northwind_ai", "healthy", 890, 65, 22, 80),
    ("Brightpath", "brightpath_co", "healthy", 1500, 70, 40, 120),
    ("Cedar Analytics", "cedar_analytics", "healthy", 2100, 71, 48, 160),
    ("Harbor Systems", "harbor_systems", "healthy", 980, 66, 25, 90),
    ("Lumen Data", "lumen_data", "healthy", 2750, 73, 50, 200),
    ("Vertex Ops", "vertex_ops", "healthy", 1200, 69, 32, 100),
    ("Praxis Software", "praxis_sw", "healthy", 1650, 67, 38, 130),
    ("Summit GTM", "summit_gtm", "healthy", 2900, 75, 52, 210),
    ("Relay Works", "relay_works", "healthy", 740, 64, 18, 70),
    ("Copperfield AI", "copperfield_ai", "healthy", 1980, 72, 42, 140),
    ("Atlas Reply", "atlas_reply", "healthy", 1100, 68, 30, 95),
    ("Forge Legal", "forge_legal", "healthy", 3400, 76, 58, 240),
    ("Pilot Metrics", "pilot_metrics", "healthy", 860, 63, 20, 75),
    ("Sable Cloud", "sable_cloud", "healthy", 2200, 70, 46, 170),
    ("Quill Research", "quill_research", "healthy", 1320, 69, 34, 105),
    ("Nimbus HR", "nimbus_hr", "healthy", 1750, 71, 39, 125),
    ("Orbit Finance", "orbit_finance", "healthy", 2550, 73, 49, 190),
    ("CloudNine Sub", "cloudnine_sub", "healthy", 6200, 58, 120, 2800),
    ("Solaris Digital", "solaris_digital", "healthy", 4800, 55, 95, 2200),
    ("Matterhorn AG", "matterhorn_ag", "healthy", 9100, 52, 180, 4500),
    ("Pixel Forge", "pixel_forge", "healthy", 5400, 57, 110, 2600),
    ("Nebula Studio", "nebula_studio", "healthy", 3900, 59, 85, 1800),
    ("Redwood Compliance", "redwood_compliance", "healthy", 7200, 54, 140, 3500),
    ("Cascade BI", "cascade_bi", "healthy", 4500, 56, 100, 2100),
    ("Ironclad Ops", "ironclad_ops", "healthy", 8800, 53, 165, 4200),
    ("Beacon Trust", "beacon_trust", "healthy", 6700, 58, 130, 3100),
    ("Horizon Legal", "horizon_legal", "healthy", 5100, 57, 105, 2400),
    ("Overrun Analytics", "overrun_analytics", "marginal", 1800, 18, 95, 400),
    ("Bleeding Edge Co", "bleeding_edge_co", "unprofitable", 2400, 12, 110, 800),
    ("Budget Buster LLC", "budget_buster_llc", "marginal", 950, 8, 55, 150),
]


def _build_filler_persona(
    display_name: str,
    external_id: str,
    archetype: str,
    revenue: float,
    target_margin_pct: float,
    runs_per_day: float,
    budget: float,
) -> Persona:
    """Derive cost/run from target margin (30-day MTD approximation)."""
    cost_month = revenue * (1 - target_margin_pct / 100)
    runs_per_day = min(runs_per_day, 45)
    runs_month = max(runs_per_day * 30, 1)
    cost_per_run = max(cost_month / runs_month, 0.004)

    return Persona(
        external_id=external_id,
        display_name=display_name,
        archetype=archetype,  # type: ignore[arg-type]
        monthly_revenue_usd=revenue,
        monthly_budget_usd=budget,
        runs_per_day_mean=runs_per_day,
        runs_per_day_stddev=max(runs_per_day * 0.25, 3),
        cost_per_run_mean=round(cost_per_run, 4),
        cost_per_run_stddev=round(cost_per_run * 0.15, 4),
        workflows={"summarize": 0.5, "extract": 0.3, "classify": 0.2},
        models={"gpt-4o-mini": 0.9, "claude-3-5-haiku": 0.1},
        anomaly_rate=0.01 if archetype == "marginal" else 0.005,
        avg_input_tokens=700,
        avg_output_tokens=180,
    )


FILLER_PERSONAS: list[Persona] = [
    _build_filler_persona(*spec) for spec in _FILLER_SPECS
]

assert len(FILLER_PERSONAS) == 33
