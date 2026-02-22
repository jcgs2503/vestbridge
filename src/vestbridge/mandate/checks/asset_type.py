"""Asset type check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from vestbridge.mandate.models import CheckResult, MandatePermissions

if TYPE_CHECKING:
    from vestbridge.brokers.base import OrderRequest
    from vestbridge.mandate.engine import TradingContext


class AssetTypeCheck:
    """Check that asset_type is in allowed_asset_types (if set)."""

    name = "asset_type"

    def evaluate(
        self, order: OrderRequest, permissions: MandatePermissions, context: TradingContext
    ) -> CheckResult:
        if permissions.allowed_asset_types is None:
            return CheckResult(check_name=self.name, passed=True)

        allowed = [t.lower() for t in permissions.allowed_asset_types]
        if order.asset_type.value.lower() not in allowed:
            return CheckResult(
                check_name=self.name,
                passed=False,
                reason=(
                    f"Asset type '{order.asset_type.value}' is not allowed. "
                    f"Allowed: {', '.join(permissions.allowed_asset_types)}"
                ),
            )
        return CheckResult(check_name=self.name, passed=True)
