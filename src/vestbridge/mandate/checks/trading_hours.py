"""Trading hours, order type, and side checks."""

from __future__ import annotations

from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext

ET = ZoneInfo("America/New_York")
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0


class TradingHoursCheck:
    """Check that current time is within US market hours (9:30-16:00 ET, weekdays)."""

    name = "trading_hours"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if not permissions.trading_hours_only:
            return CheckResult(check_name=self.name, passed=True)

        et_time = context.current_time.astimezone(ET)

        # Check weekday (0=Mon, 6=Sun)
        if et_time.weekday() >= 5:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason="Trading restricted to weekdays only (market is closed)",
            )

        current_minutes = et_time.hour * 60 + et_time.minute
        market_open = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MINUTE
        market_close = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MINUTE

        if current_minutes < market_open or current_minutes >= market_close:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Outside market hours. Current ET time: {et_time.strftime('%H:%M')}. "
                    f"Market hours: 09:30-16:00 ET"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)


class OrderTypeCheck:
    """Check that order_type is in allowed_order_types (if set)."""

    name = "order_type"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.allowed_order_types is None:
            return CheckResult(check_name=self.name, passed=True)

        allowed = [t.lower() for t in permissions.allowed_order_types]
        if order.order_type.value.lower() not in allowed:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Order type '{order.order_type.value}' is not allowed. "
                    f"Allowed: {', '.join(permissions.allowed_order_types)}"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)


class SideCheck:
    """Check that side is in allowed_sides (if set)."""

    name = "side"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.allowed_sides is None:
            return CheckResult(check_name=self.name, passed=True)

        allowed = [s.lower() for s in permissions.allowed_sides]
        if order.side.value.lower() not in allowed:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Side '{order.side.value}' is not allowed. "
                    f"Allowed: {', '.join(permissions.allowed_sides)}"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)
