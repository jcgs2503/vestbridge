"""get_quote tool implementation."""

from vestbridge.audit.logger import AuditLogger
from vestbridge.brokers.base import BrokerAdapter


async def handle_get_quote(
    symbol: str,
    *,
    broker_adapter: BrokerAdapter,
    audit_logger: AuditLogger,
    agent_id: str,
) -> dict:
    """Get current price quote for a symbol."""
    quote = await broker_adapter.get_quote(symbol)

    audit_logger.log(
        agent_id=agent_id,
        action="get_quote",
        params={"symbol": symbol},
        result=quote.model_dump(mode="json"),
    )
    return quote.model_dump(mode="json")
