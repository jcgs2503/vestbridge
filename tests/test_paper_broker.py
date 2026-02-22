"""Tests for paper trading broker adapter."""

from pathlib import Path

import pytest

from vestbridge.brokers.base import OrderRequest, OrderType, Side
from vestbridge.brokers.paper import PaperBroker


@pytest.fixture
def broker(tmp_path: Path) -> PaperBroker:
    return PaperBroker(state_path=tmp_path / "paper_state.json")


@pytest.mark.asyncio
async def test_initial_account(broker: PaperBroker):
    account = await broker.get_account()
    assert account.cash_balance == 100_000.0
    assert account.portfolio_value == 100_000.0
    assert account.positions_value == 0.0


@pytest.mark.asyncio
async def test_get_quote(broker: PaperBroker):
    quote = await broker.get_quote("AAPL")
    assert quote.symbol == "AAPL"
    assert quote.price > 0
    assert quote.bid is not None
    assert quote.ask is not None


@pytest.mark.asyncio
async def test_buy_order(broker: PaperBroker):
    order = OrderRequest(symbol="AAPL", qty=10, side=Side.BUY, order_type=OrderType.MARKET)
    result = await broker.place_order(order)
    assert result.status == "filled"
    assert result.filled_qty == 10
    assert result.filled_price > 0

    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].qty == 10

    account = await broker.get_account()
    assert account.cash_balance < 100_000.0


@pytest.mark.asyncio
async def test_sell_order(broker: PaperBroker):
    # Buy first
    buy = OrderRequest(symbol="AAPL", qty=10, side=Side.BUY, order_type=OrderType.MARKET)
    await broker.place_order(buy)

    # Then sell
    sell = OrderRequest(symbol="AAPL", qty=5, side=Side.SELL, order_type=OrderType.MARKET)
    result = await broker.place_order(sell)
    assert result.status == "filled"

    positions = await broker.get_positions()
    assert positions[0].qty == 5


@pytest.mark.asyncio
async def test_sell_all_removes_position(broker: PaperBroker):
    buy = OrderRequest(symbol="AAPL", qty=10, side=Side.BUY, order_type=OrderType.MARKET)
    await broker.place_order(buy)

    sell = OrderRequest(symbol="AAPL", qty=10, side=Side.SELL, order_type=OrderType.MARKET)
    await broker.place_order(sell)

    positions = await broker.get_positions()
    assert len(positions) == 0


@pytest.mark.asyncio
async def test_insufficient_funds(broker: PaperBroker):
    # Try to buy more than we can afford
    order = OrderRequest(symbol="AAPL", qty=100000, side=Side.BUY, order_type=OrderType.MARKET)
    result = await broker.place_order(order)
    assert result.status == "rejected"
    assert "Insufficient funds" in result.message


@pytest.mark.asyncio
async def test_insufficient_shares(broker: PaperBroker):
    order = OrderRequest(symbol="AAPL", qty=10, side=Side.SELL, order_type=OrderType.MARKET)
    result = await broker.place_order(order)
    assert result.status == "rejected"
    assert "Insufficient shares" in result.message


@pytest.mark.asyncio
async def test_limit_order_pending(broker: PaperBroker):
    # Get current price
    quote = await broker.get_quote("AAPL")
    # Set limit well below market — should pend
    order = OrderRequest(
        symbol="AAPL",
        qty=10,
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        limit_price=quote.price * 0.5,
    )
    result = await broker.place_order(order)
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_cancel_pending_order(broker: PaperBroker):
    quote = await broker.get_quote("AAPL")
    order = OrderRequest(
        symbol="AAPL",
        qty=10,
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        limit_price=quote.price * 0.5,
    )
    result = await broker.place_order(order)

    cancel = await broker.cancel_order(result.order_id)
    assert cancel.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_nonexistent_order(broker: PaperBroker):
    cancel = await broker.cancel_order("fake_order_123")
    assert cancel.status == "rejected"


@pytest.mark.asyncio
async def test_state_persistence(tmp_path: Path):
    state_path = tmp_path / "state.json"

    # First broker instance — buy shares
    b1 = PaperBroker(state_path=state_path)
    order = OrderRequest(symbol="AAPL", qty=10, side=Side.BUY, order_type=OrderType.MARKET)
    await b1.place_order(order)

    # New instance — should load persisted state
    b2 = PaperBroker(state_path=state_path)
    positions = await b2.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].qty == 10
