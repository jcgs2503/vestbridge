"""MCP server setup and tool registration."""

import hashlib
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

from vestbridge.audit.logger import AuditLogger
from vestbridge.brokers.base import AssetType, OrderRequest, OrderType, Side
from vestbridge.brokers.paper import PaperBroker
from vestbridge.config import MANDATES_DIR, ensure_dirs
from vestbridge.identity.agent import get_agent_audit_path, get_or_create_default_agent
from vestbridge.mandate.engine import MandateEngine, TradingContext
from vestbridge.mandate.loader import load_mandate_from_dir

mcp = FastMCP("vestbridge")


def _get_broker(broker: str | None = None) -> PaperBroker:
    """Get a broker adapter by name. Only paper is implemented."""
    name = broker or "paper"
    if name != "paper":
        raise ValueError(f"Broker '{name}' is not yet supported. Use 'paper' for now.")
    return PaperBroker()


def _get_context() -> tuple[str, AuditLogger]:
    """Get agent ID and audit logger for the current session."""
    ensure_dirs()
    agent = get_or_create_default_agent()
    audit_path = get_agent_audit_path(agent.agent_id)
    return agent.agent_id, AuditLogger(audit_path)


def _mandate_hash(mandate_path_name: str = "default") -> str | None:
    """Compute hash of the mandate file for audit entries."""
    path = MANDATES_DIR / f"{mandate_path_name}.yaml"
    if not path.exists():
        path = MANDATES_DIR / f"{mandate_path_name}.yml"
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


@mcp.tool()
async def get_quote(symbol: str, broker: str | None = None) -> dict:
    """Get current price quote for a symbol.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, NVDA)
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    b = _get_broker(broker)
    quote = await b.get_quote(symbol)

    audit.log(
        agent_id=agent_id,
        action="get_quote",
        params={"symbol": symbol, "broker": broker or "paper"},
        result=quote.model_dump(mode="json"),
    )
    return quote.model_dump(mode="json")


@mcp.tool()
async def get_positions(broker: str | None = None) -> list[dict]:
    """Get all current positions.

    Args:
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    b = _get_broker(broker)
    positions = await b.get_positions()

    audit.log(
        agent_id=agent_id,
        action="get_positions",
        params={"broker": broker or "paper"},
        result={"positions": [p.model_dump(mode="json") for p in positions]},
    )
    return [p.model_dump(mode="json") for p in positions]


@mcp.tool()
async def get_account(broker: str | None = None) -> dict:
    """Get account balance, buying power, and portfolio value.

    Args:
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    b = _get_broker(broker)
    account = await b.get_account()

    audit.log(
        agent_id=agent_id,
        action="get_account",
        params={"broker": broker or "paper"},
        result=account.model_dump(mode="json"),
    )
    return account.model_dump(mode="json")


@mcp.tool()
async def place_order(
    symbol: str,
    qty: float,
    side: str,
    order_type: str = "market",
    limit_price: float | None = None,
    broker: str | None = None,
) -> dict:
    """Place a trade order. Subject to mandate validation.

    Args:
        symbol: Stock ticker symbol
        qty: Number of shares
        side: Order side - "buy", "sell", or "short"
        order_type: Order type - "market", "limit", or "stop"
        limit_price: Required for limit orders
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    b = _get_broker(broker)

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

    # Load mandate and run checks
    mandate_id = None
    mhash = None
    try:
        mandate = load_mandate_from_dir(MANDATES_DIR)
        mandate_id = mandate.mandate_id
        mhash = _mandate_hash()

        # Build trading context
        positions = await b.get_positions()
        account = await b.get_account()
        quote = await b.get_quote(symbol)
        daily_notional, daily_trade_count = audit.get_daily_stats(agent_id)

        context = TradingContext(
            positions=positions,
            portfolio_value=account.portfolio_value,
            daily_notional=daily_notional,
            daily_trade_count=daily_trade_count,
            current_time=datetime.now(UTC),
            current_price=quote.price,
        )

        engine = MandateEngine(mandate)
        result = engine.evaluate(order, context)

        if not result.passed:
            audit.log(
                agent_id=agent_id,
                action="place_order",
                params=params,
                mandate_id=mandate_id,
                mandate_hash=mhash,
                mandate_check="FAIL",
                mandate_reason=result.blocked_reason,
            )
            return {
                "status": "blocked",
                "reason": result.blocked_reason,
                "message": f"Order blocked: {result.blocked_reason}. Adjust your strategy.",
                "checks": [c.model_dump() for c in result.checks],
            }
    except FileNotFoundError:
        # No mandate file — proceed without mandate checks
        pass

    # All checks passed (or no mandate) — send to broker
    order_result = await b.place_order(order)

    audit.log(
        agent_id=agent_id,
        action="place_order",
        params=params,
        mandate_id=mandate_id,
        mandate_hash=mhash,
        mandate_check="PASS" if mandate_id else None,
        result=order_result.model_dump(mode="json"),
    )
    return order_result.model_dump(mode="json")


@mcp.tool()
async def cancel_order(order_id: str, broker: str | None = None) -> dict:
    """Cancel a pending order.

    Args:
        order_id: The order ID to cancel
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    b = _get_broker(broker)
    result = await b.cancel_order(order_id)

    audit.log(
        agent_id=agent_id,
        action="cancel_order",
        params={"order_id": order_id, "broker": broker or "paper"},
        result=result.model_dump(mode="json"),
    )
    return result.model_dump(mode="json")


@mcp.tool()
async def get_audit_log(n: int = 10) -> list[dict]:
    """Get recent audit log entries for the current agent.

    Args:
        n: Number of recent entries to return (default: 10)
    """
    agent_id, audit = _get_context()
    entries = audit.read_entries(last_n=n)
    return [e.model_dump(mode="json") for e in entries]
