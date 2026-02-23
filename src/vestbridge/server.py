"""MCP server setup and tool registration."""

import hashlib

from mcp.server.fastmcp import FastMCP

from vestbridge.audit.logger import AuditLogger
from vestbridge.brokers.paper import PaperBroker
from vestbridge.config import MANDATES_DIR, ensure_dirs
from vestbridge.identity.agent import get_agent_audit_path, get_or_create_default_agent
from vestbridge.mandate.engine import MandateEngine
from vestbridge.mandate.loader import load_mandate_from_dir
from vestbridge.tools.audit_view import handle_get_recent_actions
from vestbridge.tools.order import handle_cancel_order, handle_place_order
from vestbridge.tools.positions import handle_get_account, handle_get_positions
from vestbridge.tools.quote import handle_get_quote

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


def _load_mandate_engine() -> tuple[MandateEngine | None, str | None, str | None]:
    """Load mandate and create engine. Returns (engine, mandate_id, hash) or Nones."""
    try:
        mandate = load_mandate_from_dir(MANDATES_DIR)
        return MandateEngine(mandate), mandate.mandate_id, _mandate_hash()
    except FileNotFoundError:
        return None, None, None


@mcp.tool()
async def get_quote(symbol: str, broker: str | None = None) -> dict:
    """Get current price quote for a symbol.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, NVDA)
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    return await handle_get_quote(
        symbol, broker_adapter=_get_broker(broker), audit_logger=audit, agent_id=agent_id
    )


@mcp.tool()
async def get_positions(broker: str | None = None) -> list[dict]:
    """Get all current positions.

    Args:
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    return await handle_get_positions(
        broker_adapter=_get_broker(broker), audit_logger=audit, agent_id=agent_id
    )


@mcp.tool()
async def get_account(broker: str | None = None) -> dict:
    """Get account balance, buying power, and portfolio value.

    Args:
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    return await handle_get_account(
        broker_adapter=_get_broker(broker), audit_logger=audit, agent_id=agent_id
    )


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
    engine, mandate_id, mhash = _load_mandate_engine()

    return await handle_place_order(
        symbol,
        qty,
        side,
        order_type,
        limit_price,
        mandate_engine=engine,
        audit_logger=audit,
        broker_adapter=_get_broker(broker),
        agent_id=agent_id,
        mandate_id=mandate_id,
        mandate_hash=mhash,
    )


@mcp.tool()
async def cancel_order(order_id: str, broker: str | None = None) -> dict:
    """Cancel a pending order.

    Args:
        order_id: The order ID to cancel
        broker: Broker to use (default: paper)
    """
    agent_id, audit = _get_context()
    return await handle_cancel_order(
        order_id, broker_adapter=_get_broker(broker), audit_logger=audit, agent_id=agent_id
    )


@mcp.tool()
async def get_audit_log(n: int = 10) -> list[dict]:
    """Get recent audit log entries for the current agent.

    Args:
        n: Number of recent entries to return (default: 10)
    """
    agent_id, audit = _get_context()
    return handle_get_recent_actions(audit_logger=audit, agent_id=agent_id, n=n)
