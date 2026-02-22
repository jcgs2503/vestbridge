"""Pydantic models for mandate specification and evaluation results."""

from datetime import datetime

from pydantic import BaseModel, Field


class MandatePermissions(BaseModel):
    max_order_size_usd: float | None = None
    max_daily_notional_usd: float | None = None
    max_daily_trades: int | None = None
    allowed_symbols: list[str] | None = None
    blocked_symbols: list[str] | None = None
    allowed_sides: list[str] | None = None
    allowed_order_types: list[str] | None = None
    allowed_asset_types: list[str] | None = None
    max_concentration_pct: float | None = None
    max_portfolio_pct_per_order: float | None = None
    trading_hours_only: bool = False
    require_limit_orders: bool = False


class Mandate(BaseModel):
    mandate_id: str = Field(default_factory=lambda: "")
    version: int = 1
    agent_id: str | None = None
    permissions: MandatePermissions
    created_at: datetime = Field(default_factory=datetime.utcnow)
    description: str | None = None


class CheckResult(BaseModel):
    check_name: str
    passed: bool
    reason: str | None = None


class MandateResult(BaseModel):
    passed: bool
    checks: list[CheckResult]
    blocked_reason: str | None = None
