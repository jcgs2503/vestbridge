"""get_positions and get_account tool implementations."""

from vestbridge.audit.logger import AuditLogger
from vestbridge.brokers.base import BrokerAdapter


async def handle_get_positions(
    *,
    broker_adapter: BrokerAdapter,
    audit_logger: AuditLogger,
    agent_id: str,
) -> list[dict]:
    """Get all current positions."""
    positions = await broker_adapter.get_positions()

    audit_logger.log(
        agent_id=agent_id,
        action="get_positions",
        params={},
        result={"positions": [p.model_dump(mode="json") for p in positions]},
    )
    return [p.model_dump(mode="json") for p in positions]


async def handle_get_account(
    *,
    broker_adapter: BrokerAdapter,
    audit_logger: AuditLogger,
    agent_id: str,
) -> dict:
    """Get account balance, buying power, and portfolio value."""
    account = await broker_adapter.get_account()

    audit_logger.log(
        agent_id=agent_id,
        action="get_account",
        params={},
        result=account.model_dump(mode="json"),
    )
    return account.model_dump(mode="json")
