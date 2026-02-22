"""Mandate engine — pre-trade validation against mandate rules."""

from datetime import datetime, timezone

from vestbridge.brokers.base import OrderRequest, Position
from vestbridge.mandate.checks.asset_type import AssetTypeCheck
from vestbridge.mandate.checks.concentration import ConcentrationCheck
from vestbridge.mandate.checks.daily_volume import DailyTradeCountCheck, DailyVolumeCheck
from vestbridge.mandate.checks.order_size import OrderSizeCheck, PortfolioPercentCheck
from vestbridge.mandate.checks.symbol_allow import SymbolAllowlistCheck, SymbolBlocklistCheck
from vestbridge.mandate.checks.trading_hours import OrderTypeCheck, SideCheck, TradingHoursCheck
from vestbridge.mandate.models import CheckResult, Mandate, MandatePermissions, MandateResult


class TradingContext:
    """Context required to evaluate mandate checks against an order."""

    def __init__(
        self,
        positions: list[Position],
        portfolio_value: float,
        daily_notional: float = 0.0,
        daily_trade_count: int = 0,
        current_time: datetime | None = None,
        current_price: float | None = None,
    ) -> None:
        self.positions = positions
        self.portfolio_value = portfolio_value
        self.daily_notional = daily_notional
        self.daily_trade_count = daily_trade_count
        self.current_time = current_time or datetime.now(timezone.utc)
        self.current_price = current_price


class MandateCheck:
    """Base class for individual mandate checks."""

    name: str = "base_check"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        raise NotImplementedError


class MandateEngine:
    """Run all applicable mandate checks against a proposed order."""

    def __init__(self, mandate: Mandate) -> None:
        self.mandate = mandate
        self.checks = self._load_checks()

    def _load_checks(self) -> list[MandateCheck]:
        return [
            OrderSizeCheck(),
            ConcentrationCheck(),
            SymbolAllowlistCheck(),
            SymbolBlocklistCheck(),
            AssetTypeCheck(),
            DailyVolumeCheck(),
            DailyTradeCountCheck(),
            TradingHoursCheck(),
            OrderTypeCheck(),
            SideCheck(),
            PortfolioPercentCheck(),
        ]

    def evaluate(self, order: OrderRequest, context: TradingContext) -> MandateResult:
        results: list[CheckResult] = []
        for check in self.checks:
            result = check.evaluate(order, self.mandate.permissions, context)
            results.append(result)

        passed = all(r.passed for r in results)
        blocked_reasons = [r.reason for r in results if not r.passed and r.reason]

        return MandateResult(
            passed=passed,
            checks=results,
            blocked_reason="; ".join(blocked_reasons) if blocked_reasons else None,
        )
