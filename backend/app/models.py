from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ModelUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    usd: float


class CostEventIn(BaseModel):
    run_id: str = Field(..., min_length=8, max_length=64)
    workspace_id: str
    customer_id: str = Field(..., min_length=1, max_length=128)
    workflow_id: Optional[str] = "default"
    ts: int
    status: str = Field(..., pattern="^(completed|error|budget_exceeded)$")
    total_usd: float = Field(..., ge=0)
    models: dict[str, ModelUsage] = {}
    node_costs: dict[str, float] = {}
    metadata: dict = {}
    error: Optional[str] = None


class BudgetResponse(BaseModel):
    status: str
    spent_usd: float
    budget_usd: Optional[float]
    remaining_usd: float


class CustomerIn(BaseModel):
    external_id: str
    display_name: Optional[str] = None
    monthly_budget_usd: Optional[float] = None
    monthly_revenue_usd: Optional[float] = None
    stripe_customer_id: Optional[str] = None


class CustomerUpdate(BaseModel):
    display_name: Optional[str] = None
    monthly_budget_usd: Optional[float] = None
    monthly_revenue_usd: Optional[float] = None
    stripe_customer_id: Optional[str] = None


class CustomerImportRow(BaseModel):
    external_id: str = Field(..., min_length=1, max_length=128)
    display_name: Optional[str] = None
    monthly_budget_usd: Optional[float] = None
    monthly_revenue_usd: Optional[float] = None
    stripe_customer_id: Optional[str] = None


class CustomerImportIn(BaseModel):
    customers: list[CustomerImportRow]
    mode: str = Field(default="upsert", pattern="^(upsert)$")


class LeaderboardRow(BaseModel):
    customer_id: str
    external_id: str
    display_name: str
    runs: int
    cost_usd: float
    revenue_usd: float
    margin_pct: float
    budget_status: str
