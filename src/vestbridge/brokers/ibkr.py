"""Interactive Brokers adapter (stub)."""

from vestbridge.brokers.base import (
    Account,
    BrokerAdapter,
    CancelResult,
    OrderRequest,
    OrderResult,
    Position,
    Quote,
)


class IBKRAdapter(BrokerAdapter):
    async def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError("Interactive Brokers adapter coming soon")

    async def get_positions(self) -> list[Position]:
        raise NotImplementedError("Interactive Brokers adapter coming soon")

    async def get_account(self) -> Account:
        raise NotImplementedError("Interactive Brokers adapter coming soon")

    async def place_order(self, order: OrderRequest) -> OrderResult:
        raise NotImplementedError("Interactive Brokers adapter coming soon")

    async def cancel_order(self, order_id: str) -> CancelResult:
        raise NotImplementedError("Interactive Brokers adapter coming soon")
