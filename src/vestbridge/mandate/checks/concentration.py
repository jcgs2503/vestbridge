"""Single-stock concentration check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext


class ConcentrationCheck:
    """Check that (existing position + order) / portfolio_value does not exceed max_concentration_pct."""

    name = "concentration"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.max_concentration_pct is None:
            return CheckResult(check_name=self.name, passed=True)

        if context.portfolio_value <= 0:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason="Cannot evaluate concentration: portfolio value is zero",
            )

        price = context.current_price or 0.0

        # Find existing position in this symbol
        existing_value = 0.0
        for pos in context.positions:
            if pos.symbol.upper() == order.symbol.upper():
                existing_value = pos.market_value
                break

        order_value = price * order.qty
        total_value = existing_value + order_value
        concentration_pct = (total_value / context.portfolio_value) * 100

        if concentration_pct > permissions.max_concentration_pct:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"{order.symbol} would be {concentration_pct:.1f}% of portfolio, "
                    f"exceeds max concentration {permissions.max_concentration_pct}%"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)
