"""Symbol allowlist and blocklist checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext


class SymbolAllowlistCheck:
    """Check that symbol is in allowed_symbols (if set)."""

    name = "symbol_allowlist"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.allowed_symbols is None:
            return CheckResult(check_name=self.name, passed=True)

        allowed = [s.upper() for s in permissions.allowed_symbols]
        if order.symbol.upper() not in allowed:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=f"{order.symbol} is not in allowed symbols list",
            )
        return CheckResult(check_name=self.name, passed=True)


class SymbolBlocklistCheck:
    """Check that symbol is not in blocked_symbols (if set)."""

    name = "symbol_blocklist"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.blocked_symbols is None:
            return CheckResult(check_name=self.name, passed=True)

        blocked = [s.upper() for s in permissions.blocked_symbols]
        if order.symbol.upper() in blocked:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=f"{order.symbol} is in blocked symbols list",
            )
        return CheckResult(check_name=self.name, passed=True)
