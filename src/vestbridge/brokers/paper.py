"""Paper trading broker adapter for testing and demos."""

import json
import random
import uuid
from datetime import UTC, datetime
from pathlib import Path

from vestbridge.brokers.base import (
    Account,
    BrokerAdapter,
    CancelResult,
    OrderRequest,
    OrderResult,
    OrderStatus,
    OrderType,
    Position,
    Quote,
    Side,
)
from vestbridge.config import PAPER_DIR

DEFAULT_CASH = 100_000.0
STATE_FILE = PAPER_DIR / "state.json"


class PaperState:
    """In-memory state for paper trading, persisted to disk."""

    def __init__(self) -> None:
        self.cash: float = DEFAULT_CASH
        self.positions: dict[str, dict] = {}  # symbol -> {qty, avg_cost}
        self.pending_orders: dict[str, dict] = {}  # order_id -> order dict
        self.prices: dict[str, float] = {}  # symbol -> last known price

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "positions": self.positions,
            "pending_orders": self.pending_orders,
            "prices": self.prices,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PaperState":
        state = cls()
        state.cash = data.get("cash", DEFAULT_CASH)
        state.positions = data.get("positions", {})
        state.pending_orders = data.get("pending_orders", {})
        state.prices = data.get("prices", {})
        return state


class PaperBroker(BrokerAdapter):
    """Fully functional paper trading adapter.

    - Maintains in-memory positions and cash balance
    - Simulates fills at current price with small random spread
    - Supports market and limit orders
    - Persists state to ~/.vest/paper/state.json between runs
    - Default starting cash: $100,000
    """

    def __init__(self, state_path: Path | None = None) -> None:
        self.state_path = state_path or STATE_FILE
        self.state = self._load_state()

    def _load_state(self) -> PaperState:
        if self.state_path.exists():
            with open(self.state_path) as f:
                return PaperState.from_dict(json.load(f))
        return PaperState()

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self.state.to_dict(), f, indent=2)

    def _get_simulated_price(self, symbol: str) -> float:
        """Get or generate a simulated price for a symbol."""
        if symbol not in self.state.prices:
            # Generate a reasonable starting price
            self.state.prices[symbol] = round(random.uniform(20.0, 500.0), 2)
        else:
            # Small random walk from last price
            last = self.state.prices[symbol]
            change = last * random.uniform(-0.02, 0.02)
            self.state.prices[symbol] = round(max(0.01, last + change), 2)
        return self.state.prices[symbol]

    def _portfolio_value(self) -> float:
        positions_value = sum(
            pos["qty"] * self._get_simulated_price(symbol)
            for symbol, pos in self.state.positions.items()
            if pos["qty"] > 0
        )
        return self.state.cash + positions_value

    async def get_quote(self, symbol: str) -> Quote:
        price = self._get_simulated_price(symbol)
        spread = price * 0.001  # 0.1% spread
        return Quote(
            symbol=symbol.upper(),
            price=price,
            bid=round(price - spread, 2),
            ask=round(price + spread, 2),
            volume=random.randint(100_000, 10_000_000),
            timestamp=datetime.now(UTC),
        )

    async def get_positions(self) -> list[Position]:
        positions = []
        for symbol, pos in self.state.positions.items():
            if pos["qty"] <= 0:
                continue
            current_price = self._get_simulated_price(symbol)
            market_value = pos["qty"] * current_price
            cost_basis = pos["qty"] * pos["avg_cost"]
            positions.append(
                Position(
                    symbol=symbol,
                    qty=pos["qty"],
                    avg_cost=pos["avg_cost"],
                    current_price=current_price,
                    market_value=round(market_value, 2),
                    unrealized_pnl=round(market_value - cost_basis, 2),
                )
            )
        return positions

    async def get_account(self) -> Account:
        positions_value = sum(
            pos["qty"] * self._get_simulated_price(symbol)
            for symbol, pos in self.state.positions.items()
            if pos["qty"] > 0
        )
        portfolio_value = self.state.cash + positions_value
        return Account(
            account_id="paper",
            cash_balance=round(self.state.cash, 2),
            buying_power=round(self.state.cash, 2),
            portfolio_value=round(portfolio_value, 2),
            positions_value=round(positions_value, 2),
        )

    async def place_order(self, order: OrderRequest) -> OrderResult:
        symbol = order.symbol.upper()
        price = self._get_simulated_price(symbol)
        order_id = f"paper_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC)

        # Handle limit orders
        if order.order_type == OrderType.LIMIT:
            if order.limit_price is None:
                return OrderResult(
                    order_id=order_id,
                    symbol=symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.REJECTED,
                    message="Limit orders require a limit_price",
                    timestamp=now,
                )
            # Check if limit price is favorable
            if order.side == Side.BUY and order.limit_price < price:
                # Store as pending — in real life would fill when price drops
                self.state.pending_orders[order_id] = {
                    "symbol": symbol,
                    "qty": order.qty,
                    "side": order.side.value,
                    "limit_price": order.limit_price,
                    "timestamp": now.isoformat(),
                }
                self._save_state()
                return OrderResult(
                    order_id=order_id,
                    symbol=symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.PENDING,
                    message=f"Limit order pending (limit {order.limit_price} < market {price})",
                    timestamp=now,
                )
            if order.side == Side.SELL and order.limit_price > price:
                self.state.pending_orders[order_id] = {
                    "symbol": symbol,
                    "qty": order.qty,
                    "side": order.side.value,
                    "limit_price": order.limit_price,
                    "timestamp": now.isoformat(),
                }
                self._save_state()
                return OrderResult(
                    order_id=order_id,
                    symbol=symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.PENDING,
                    message=f"Limit order pending (limit {order.limit_price} > market {price})",
                    timestamp=now,
                )
            # Limit price is favorable, fill immediately
            fill_price = order.limit_price
        else:
            # Market order — fill at current price
            fill_price = price

        # Execute the fill
        total_cost = fill_price * order.qty

        if order.side == Side.BUY:
            if total_cost > self.state.cash:
                return OrderResult(
                    order_id=order_id,
                    symbol=symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.REJECTED,
                    message=(
                        f"Insufficient funds: need ${total_cost:.2f}, have ${self.state.cash:.2f}"
                    ),
                    timestamp=now,
                )
            self.state.cash -= total_cost
            if symbol in self.state.positions:
                existing = self.state.positions[symbol]
                new_qty = existing["qty"] + order.qty
                new_cost = (existing["qty"] * existing["avg_cost"] + total_cost) / new_qty
                self.state.positions[symbol] = {"qty": new_qty, "avg_cost": round(new_cost, 4)}
            else:
                self.state.positions[symbol] = {"qty": order.qty, "avg_cost": fill_price}

        elif order.side == Side.SELL:
            has_shares = symbol in self.state.positions
            if not has_shares or self.state.positions[symbol]["qty"] < order.qty:
                available = self.state.positions.get(symbol, {}).get("qty", 0)
                return OrderResult(
                    order_id=order_id,
                    symbol=symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.REJECTED,
                    message=f"Insufficient shares: need {order.qty}, have {available}",
                    timestamp=now,
                )
            self.state.cash += total_cost
            self.state.positions[symbol]["qty"] -= order.qty
            if self.state.positions[symbol]["qty"] == 0:
                del self.state.positions[symbol]

        self._save_state()
        return OrderResult(
            order_id=order_id,
            symbol=symbol,
            qty=order.qty,
            side=order.side,
            order_type=order.order_type,
            status=OrderStatus.FILLED,
            filled_price=fill_price,
            filled_qty=order.qty,
            message=f"Filled {order.qty} {symbol} @ ${fill_price:.2f}",
            timestamp=now,
        )

    async def cancel_order(self, order_id: str) -> CancelResult:
        if order_id in self.state.pending_orders:
            del self.state.pending_orders[order_id]
            self._save_state()
            return CancelResult(
                order_id=order_id,
                status=OrderStatus.CANCELLED,
                message="Order cancelled",
            )
        return CancelResult(
            order_id=order_id,
            status=OrderStatus.REJECTED,
            message=f"Order {order_id} not found or already filled",
        )
