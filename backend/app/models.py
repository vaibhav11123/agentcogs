from datetime import datetime, timezone
import json
import math
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ModelUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    usd: float

    @field_validator("usd")
    @classmethod
    def finite_usd(cls, v: float) -> float:
        if not math.isfinite(v) or v >= 1_000_000:
            raise ValueError("usd must be finite and < 1000000")
        return v


class CostEventIn(BaseModel):
    run_id: str = Field(..., min_length=8, max_length=64)
    workspace_id: Optional[str] = None
    customer_id: str = Field(..., min_length=1, max_length=128)
    workflow_id: Optional[str] = "default"
    ts: int
    status: str = Field(..., pattern="^(completed|error|budget_exceeded)$")
    total_usd: float = Field(..., ge=0)
    models: dict[str, ModelUsage] = {}
    node_costs: dict[str, float] = {}
    metadata: dict = {}
    error: Optional[str] = None

    @field_validator("total_usd")
    @classmethod
    def finite_total(cls, v: float) -> float:
        if not math.isfinite(v) or v >= 1_000_000:
            raise ValueError("total_usd must be finite and < 1000000")
        return v

    @field_validator("ts")
    @classmethod
    def ts_in_range(cls, v: int) -> int:
        now = int(datetime.now(timezone.utc).timestamp())
        if v < now - 30 * 86400:
            raise ValueError("ts is older than 30 days")
        if v > now + 300:
            raise ValueError("ts is more than 5 minutes in the future")
        return v

    @model_validator(mode="after")
    def caps_and_node_costs(self) -> "CostEventIn":
        if len(self.models) > 50:
            raise ValueError("models dict exceeds 50 entries")
        if len(self.node_costs) > 200:
            raise ValueError("node_costs exceeds 200 entries")
        if len(self.metadata) > 100:
            raise ValueError("metadata exceeds 100 keys")
        meta_size = len(json.dumps(self.metadata, default=str))
        if meta_size > 16_384:
            raise ValueError("metadata serialized size exceeds 16KB")
        for val in self.node_costs.values():
            if not math.isfinite(val) or val >= 1_000_000:
                raise ValueError("node_costs values must be finite and < 1000000")
        return self


class BudgetResponse(BaseModel):
    status: str
    spent_usd: float
    budget_usd: Optional[float]
    remaining_usd: float
    source: str = "redis"


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
