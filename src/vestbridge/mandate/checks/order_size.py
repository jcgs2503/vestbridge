"""Order size and portfolio percentage checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext


class OrderSizeCheck:
    """Check that order USD value does not exceed max_order_size_usd."""

    name = "order_size"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.max_order_size_usd is None:
            return CheckResult(check_name=self.name, passed=True)

        price = context.current_price or 0.0
        order_value = price * order.qty

        if order_value > permissions.max_order_size_usd:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Order value ${order_value:,.2f} exceeds max order size "
                    f"${permissions.max_order_size_usd:,.2f}"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)


class PortfolioPercentCheck:
    """Check that order value / portfolio_value does not exceed max_portfolio_pct_per_order."""

    name = "portfolio_percent"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.max_portfolio_pct_per_order is None:
            return CheckResult(check_name=self.name, passed=True)

        if context.portfolio_value <= 0:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason="Cannot evaluate portfolio percent: portfolio value is zero",
            )

        price = context.current_price or 0.0
        order_value = price * order.qty
        order_pct = (order_value / context.portfolio_value) * 100

        if order_pct > permissions.max_portfolio_pct_per_order:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Order is {order_pct:.1f}% of portfolio, "
                    f"exceeds max {permissions.max_portfolio_pct_per_order}%"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)
