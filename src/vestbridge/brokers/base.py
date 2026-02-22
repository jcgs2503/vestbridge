"""Abstract broker interface and shared data models."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class AssetType(str, Enum):
    EQUITY = "equity"
    OPTION = "option"
    FUTURE = "future"
    CRYPTO = "crypto"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Quote(BaseModel):
    symbol: str
    price: float
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    timestamp: datetime


class Position(BaseModel):
    symbol: str
    qty: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    asset_type: AssetType = AssetType.EQUITY


class Account(BaseModel):
    account_id: str
    cash_balance: float
    buying_power: float
    portfolio_value: float
    positions_value: float


class OrderRequest(BaseModel):
    symbol: str
    qty: float
    side: Side
    order_type: OrderType
    limit_price: float | None = None
    asset_type: AssetType = AssetType.EQUITY


class OrderResult(BaseModel):
    order_id: str
    symbol: str
    qty: float
    side: Side
    order_type: OrderType
    status: OrderStatus
    filled_price: float | None = None
    filled_qty: float | None = None
    message: str | None = None
    timestamp: datetime


class CancelResult(BaseModel):
    order_id: str
    status: OrderStatus
    message: str | None = None


class BrokerAdapter(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def get_account(self) -> Account: ...

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> CancelResult: ...
