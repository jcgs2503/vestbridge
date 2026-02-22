"""Daily volume and trade count checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext


class DailyVolumeCheck:
    """Check that today's total notional + this order does not exceed max_daily_notional_usd."""

    name = "daily_volume"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.max_daily_notional_usd is None:
            return CheckResult(check_name=self.name, passed=True)

        price = context.current_price or 0.0
        order_value = price * order.qty
        new_total = context.daily_notional + order_value

        if new_total > permissions.max_daily_notional_usd:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Daily notional would be ${new_total:,.2f}, "
                    f"exceeds max ${permissions.max_daily_notional_usd:,.2f} "
                    f"(already traded ${context.daily_notional:,.2f} today)"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)


class DailyTradeCountCheck:
    """Check that today's trade count does not exceed max_daily_trades."""

    name = "daily_trade_count"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.max_daily_trades is None:
            return CheckResult(check_name=self.name, passed=True)

        if context.daily_trade_count >= permissions.max_daily_trades:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Already placed {context.daily_trade_count} trades today, "
                    f"max is {permissions.max_daily_trades}"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)
