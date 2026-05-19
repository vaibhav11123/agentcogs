"""Mock customer personas modeled on real LangGraph SaaS patterns.

Each persona has:
- A realistic usage shape (low/medium/high volume)
- A workflow mix (which agent paths they hit)
- A model mix (gpt-4o-mini vs claude-sonnet vs gpt-4o)
- A revenue tier ($/mo paid to the founder)
- Probabilistic anomaly behavior (retry loops, prompt injection, etc.)
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class Persona:
    external_id: str
    display_name: str
    archetype: Literal["whale", "healthy", "marginal", "unprofitable", "churning", "new"]

    monthly_revenue_usd: float
    monthly_budget_usd: float | None

    runs_per_day_mean: float
    runs_per_day_stddev: float

    cost_per_run_mean: float
    cost_per_run_stddev: float

    workflows: dict[str, float]
    models: dict[str, float]

    anomaly_rate: float = 0.0
    avg_input_tokens: int = 800
    avg_output_tokens: int = 200
    # Narrative: skip events in the last N days (churning customers)
    quiet_days_end: int = 0
    # Demo script target margin (for validation only)
    target_margin_pct: float | None = None


PRICING = {
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4o": {"input": 2.500, "output": 10.000},
    "claude-3-5-sonnet": {"input": 3.000, "output": 15.000},
    "claude-3-5-haiku": {"input": 0.800, "output": 4.000},
    "claude-3-opus": {"input": 15.000, "output": 75.000},
}


PERSONAS = [
    Persona(
        external_id="acme_corp",
        display_name="Acme Corp",
        archetype="healthy",
        monthly_revenue_usd=12_400,
        monthly_budget_usd=400,
        runs_per_day_mean=100,
        runs_per_day_stddev=22,
        cost_per_run_mean=1.03,
        cost_per_run_stddev=0.14,
        workflows={"summarize": 0.5, "extract": 0.3, "classify": 0.2},
        models={"gpt-4o-mini": 0.85, "claude-3-5-haiku": 0.15},
        anomaly_rate=0.01,
        avg_input_tokens=600,
        avg_output_tokens=180,
        target_margin_pct=75.0,
    ),
    Persona(
        external_id="techflow_inc",
        display_name="TechFlow Inc",
        archetype="unprofitable",
        monthly_revenue_usd=8_200,
        monthly_budget_usd=6_000,
        runs_per_day_mean=200,
        runs_per_day_stddev=40,
        cost_per_run_mean=0.97,
        cost_per_run_stddev=0.18,
        workflows={"research_agent": 0.6, "deep_analysis": 0.4},
        models={"claude-3-5-sonnet": 0.7, "gpt-4o": 0.3},
        anomaly_rate=0.05,
        avg_input_tokens=4200,
        avg_output_tokens=1100,
        target_margin_pct=29.0,
    ),
    Persona(
        external_id="globex_industries",
        display_name="Globex Industries",
        archetype="whale",
        monthly_revenue_usd=28_500,
        monthly_budget_usd=15_000,
        runs_per_day_mean=320,
        runs_per_day_stddev=50,
        cost_per_run_mean=1.04,
        cost_per_run_stddev=0.22,
        workflows={"contract_review": 0.4, "compliance_check": 0.35, "summarize": 0.25},
        models={"claude-3-5-sonnet": 0.6, "gpt-4o": 0.35, "claude-3-opus": 0.05},
        anomaly_rate=0.02,
        avg_input_tokens=3500,
        avg_output_tokens=900,
        target_margin_pct=65.0,
    ),
    Persona(
        external_id="initech",
        display_name="Initech",
        archetype="marginal",
        monthly_revenue_usd=2_100,
        monthly_budget_usd=1_500,
        runs_per_day_mean=45,
        runs_per_day_stddev=12,
        cost_per_run_mean=0.99,
        cost_per_run_stddev=0.22,
        workflows={"research_agent": 0.8, "summarize": 0.2},
        models={"gpt-4o": 0.5, "claude-3-5-sonnet": 0.5},
        anomaly_rate=0.12,
        avg_input_tokens=5000,
        avg_output_tokens=1500,
        target_margin_pct=35.0,
    ),
    Persona(
        external_id="hooli",
        display_name="Hooli",
        archetype="churning",
        monthly_revenue_usd=499,
        monthly_budget_usd=200,
        runs_per_day_mean=12,
        runs_per_day_stddev=8,
        cost_per_run_mean=0.018,
        cost_per_run_stddev=0.006,
        workflows={"classify": 1.0},
        models={"gpt-4o-mini": 1.0},
        anomaly_rate=0.0,
        avg_input_tokens=400,
        avg_output_tokens=100,
        quiet_days_end=14,
    ),
    Persona(
        external_id="pied_piper",
        display_name="Pied Piper",
        archetype="new",
        monthly_revenue_usd=99,
        monthly_budget_usd=50,
        runs_per_day_mean=5,
        runs_per_day_stddev=3,
        cost_per_run_mean=0.025,
        cost_per_run_stddev=0.010,
        workflows={"summarize": 0.7, "extract": 0.3},
        models={"gpt-4o-mini": 1.0},
        anomaly_rate=0.0,
        avg_input_tokens=900,
        avg_output_tokens=250,
    ),
    Persona(
        external_id="dunder_mifflin",
        display_name="Dunder Mifflin",
        archetype="new",
        monthly_revenue_usd=0,
        monthly_budget_usd=20,
        runs_per_day_mean=2,
        runs_per_day_stddev=2,
        cost_per_run_mean=0.008,
        cost_per_run_stddev=0.003,
        workflows={"summarize": 1.0},
        models={"gpt-4o-mini": 1.0},
        anomaly_rate=0.0,
        avg_input_tokens=500,
        avg_output_tokens=150,
    ),
]

from personas_filler import FILLER_PERSONAS  # noqa: E402

HERO_PERSONAS = PERSONAS
ALL_PERSONAS = PERSONAS + FILLER_PERSONAS

DEMO_WORKSPACE_NAME = "Patternstack"
DEMO_OPERATOR_EMAIL = "alex@patternstack.dev"
