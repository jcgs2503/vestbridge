"""Robinhood broker adapter (stub)."""

from vestbridge.brokers.base import (
    Account,
    BrokerAdapter,
    CancelResult,
    OrderRequest,
    OrderResult,
    Position,
    Quote,
)


class RobinhoodAdapter(BrokerAdapter):
    async def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError("Robinhood adapter coming soon")

    async def get_positions(self) -> list[Position]:
        raise NotImplementedError("Robinhood adapter coming soon")

    async def get_account(self) -> Account:
        raise NotImplementedError("Robinhood adapter coming soon")

    async def place_order(self, order: OrderRequest) -> OrderResult:
        raise NotImplementedError("Robinhood adapter coming soon")

    async def cancel_order(self, order_id: str) -> CancelResult:
        raise NotImplementedError("Robinhood adapter coming soon")
