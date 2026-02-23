"""place_order and cancel_order tool implementations."""

from datetime import UTC, datetime

from vestbridge.audit.logger import AuditLogger
from vestbridge.brokers.base import (
    AssetType,
    BrokerAdapter,
    OrderRequest,
    OrderType,
    Side,
)
from vestbridge.mandate.engine import MandateEngine, TradingContext


async def handle_place_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    limit_price: float | None = None,
    *,
    mandate_engine: MandateEngine | None,
    audit_logger: AuditLogger,
    broker_adapter: BrokerAdapter,
    agent_id: str,
    mandate_id: str | None = None,
    mandate_hash: str | None = None,
) -> dict:
    """Place a trade order, subject to mandate validation."""
    order = OrderRequest(
        symbol=symbol.upper(),
        qty=qty,
        side=Side(side),
        order_type=OrderType(order_type),
        limit_price=limit_price,
        asset_type=AssetType.EQUITY,
    )

    params = {
        "symbol": order.symbol,
        "qty": order.qty,
        "side": order.side.value,
        "order_type": order.order_type.value,
        "limit_price": order.limit_price,
    }

    # Run mandate checks if engine is available
    if mandate_engine is not None:
        positions = await broker_adapter.get_positions()
        account = await broker_adapter.get_account()
        quote = await broker_adapter.get_quote(symbol)
        daily_notional, daily_trade_count = audit_logger.get_daily_stats(agent_id)

        context = TradingContext(
            positions=positions,
            portfolio_value=account.portfolio_value,
            daily_notional=daily_notional,
            daily_trade_count=daily_trade_count,
            current_time=datetime.now(UTC),
            current_price=quote.price,
        )

        result = mandate_engine.evaluate(order, context)

        if not result.passed:
            audit_logger.log(
                agent_id=agent_id,
                action="place_order",
                params=params,
                mandate_id=mandate_id,
                mandate_hash=mandate_hash,
                mandate_check="FAIL",
                mandate_reason=result.blocked_reason,
            )
            reasons = result.blocked_reason or "Unknown mandate violation"
            return {
                "status": "blocked",
                "reason": reasons,
                "message": f"Order BLOCKED by mandate: {reasons}. Adjust your strategy.",
                "checks": [c.model_dump() for c in result.checks],
            }

    # All checks passed (or no mandate) — send to broker
    order_result = await broker_adapter.place_order(order)

    audit_logger.log(
        agent_id=agent_id,
        action="place_order",
        params=params,
        mandate_id=mandate_id,
        mandate_hash=mandate_hash,
        mandate_check="PASS" if mandate_engine else None,
        result=order_result.model_dump(mode="json"),
    )
    return order_result.model_dump(mode="json")


async def handle_cancel_order(
    order_id: str,
    *,
    broker_adapter: BrokerAdapter,
    audit_logger: AuditLogger,
    agent_id: str,
) -> dict:
    """Cancel a pending order."""
    result = await broker_adapter.cancel_order(order_id)

    audit_logger.log(
        agent_id=agent_id,
        action="cancel_order",
        params={"order_id": order_id},
        result=result.model_dump(mode="json"),
    )
    return result.model_dump(mode="json")
