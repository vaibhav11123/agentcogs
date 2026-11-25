from datetime import datetime, timezone
import json
import math
import uuid
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


class CallIn(BaseModel):
    call_id: str = Field(..., min_length=1, max_length=64)
    parent_id: Optional[str] = None
    model: Optional[str] = None
    lanes: dict[str, int]
    provider_input_tokens: Optional[int] = None


class SegmentIn(BaseModel):
    segment_id: str = Field(..., min_length=1, max_length=128)
    parent_id: Optional[str] = None
    prefix_key: str = Field(..., min_length=1, max_length=128)
    start: int
    end: int
    role: str = Field(..., pattern="^(write_5m|write_1h|write_30m|write_12h)$")
    uses: list[str]


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
    calls: Optional[list[CallIn]] = None
    segments: Optional[list[SegmentIn]] = None
    book_id: Optional[str] = None

    @field_validator("run_id")
    @classmethod
    def run_id_is_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("run_id must be a UUID")
        return v

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
        if self.calls is not None and len(self.calls) > 64:
            raise ValueError("CALLS_TOO_MANY")
        if self.segments is not None and len(self.segments) > 64:
            raise ValueError("CALLS_TOO_MANY")
        if len(self.metadata) > 100:
            raise ValueError("metadata exceeds 100 keys")
        meta_size = len(json.dumps(self.metadata, default=str))
        if meta_size > 16_384:
            raise ValueError("metadata serialized size exceeds 16KB")
        for val in self.node_costs.values():
            if not math.isfinite(val) or val >= 1_000_000:
                raise ValueError("node_costs values must be finite and < 1000000")
        return self


class IngestBatchIn(BaseModel):
    events: list[CostEventIn] = Field(..., min_length=1, max_length=100)


class BudgetResponse(BaseModel):
    status: str
    spent_usd: float
    budget_usd: Optional[float]
    remaining_usd: float
    source: str = "redis"
    hold_usd: float = 0.0
    decision: str = "ok"
    enforce: bool = False


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
