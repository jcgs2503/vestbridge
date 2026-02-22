"""Tests for mandate checks and engine."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from vestbridge.brokers.base import AssetType, OrderRequest, OrderType, Position, Side
from vestbridge.mandate.checks.asset_type import AssetTypeCheck
from vestbridge.mandate.checks.concentration import ConcentrationCheck
from vestbridge.mandate.checks.daily_volume import DailyTradeCountCheck, DailyVolumeCheck
from vestbridge.mandate.checks.order_size import OrderSizeCheck, PortfolioPercentCheck
from vestbridge.mandate.checks.symbol_allow import SymbolAllowlistCheck, SymbolBlocklistCheck
from vestbridge.mandate.checks.trading_hours import OrderTypeCheck, SideCheck, TradingHoursCheck
from vestbridge.mandate.engine import MandateEngine, TradingContext
from vestbridge.mandate.models import Mandate, MandatePermissions


def make_order(
    symbol: str = "AAPL",
    qty: float = 10,
    side: Side = Side.BUY,
    order_type: OrderType = OrderType.MARKET,
    asset_type: AssetType = AssetType.EQUITY,
) -> OrderRequest:
    return OrderRequest(
        symbol=symbol, qty=qty, side=side, order_type=order_type, asset_type=asset_type
    )


def make_context(
    portfolio_value: float = 100_000,
    current_price: float = 150.0,
    positions: list[Position] | None = None,
    daily_notional: float = 0,
    daily_trade_count: int = 0,
    current_time: datetime | None = None,
) -> TradingContext:
    return TradingContext(
        positions=positions or [],
        portfolio_value=portfolio_value,
        current_price=current_price,
        daily_notional=daily_notional,
        daily_trade_count=daily_trade_count,
        current_time=current_time or datetime.now(UTC),
    )


# --- OrderSizeCheck ---


class TestOrderSizeCheck:
    def test_pass_when_no_limit(self):
        check = OrderSizeCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_within_limit(self):
        check = OrderSizeCheck()
        perms = MandatePermissions(max_order_size_usd=10000)
        result = check.evaluate(make_order(qty=10), perms, make_context(current_price=150))
        assert result.passed  # 10 * 150 = 1500

    def test_fail_exceeds_limit(self):
        check = OrderSizeCheck()
        perms = MandatePermissions(max_order_size_usd=1000)
        result = check.evaluate(make_order(qty=10), perms, make_context(current_price=150))
        assert not result.passed
        assert "exceeds max order size" in result.reason


# --- ConcentrationCheck ---


class TestConcentrationCheck:
    def test_pass_when_no_limit(self):
        check = ConcentrationCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_within_limit(self):
        check = ConcentrationCheck()
        perms = MandatePermissions(max_concentration_pct=20)
        # 10 * 150 = 1500, 1.5% of 100k
        result = check.evaluate(make_order(qty=10), perms, make_context(current_price=150))
        assert result.passed

    def test_fail_exceeds_limit(self):
        check = ConcentrationCheck()
        perms = MandatePermissions(max_concentration_pct=20)
        existing = Position(
            symbol="AAPL",
            qty=100,
            avg_cost=150,
            current_price=150,
            market_value=15000,
            unrealized_pnl=0,
        )
        # existing 15000 + 100*150=15000 = 30000, 30% of 100k
        result = check.evaluate(
            make_order(qty=100),
            perms,
            make_context(current_price=150, positions=[existing]),
        )
        assert not result.passed
        assert "concentration" in result.reason


# --- SymbolAllowlistCheck ---


class TestSymbolAllowlistCheck:
    def test_pass_when_no_list(self):
        check = SymbolAllowlistCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_in_allowlist(self):
        check = SymbolAllowlistCheck()
        perms = MandatePermissions(allowed_symbols=["AAPL", "MSFT"])
        result = check.evaluate(make_order(symbol="AAPL"), perms, make_context())
        assert result.passed

    def test_fail_not_in_allowlist(self):
        check = SymbolAllowlistCheck()
        perms = MandatePermissions(allowed_symbols=["MSFT", "GOOG"])
        result = check.evaluate(make_order(symbol="AAPL"), perms, make_context())
        assert not result.passed
        assert "not in allowed symbols" in result.reason


# --- SymbolBlocklistCheck ---


class TestSymbolBlocklistCheck:
    def test_pass_when_no_list(self):
        check = SymbolBlocklistCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_not_blocked(self):
        check = SymbolBlocklistCheck()
        perms = MandatePermissions(blocked_symbols=["GME", "AMC"])
        result = check.evaluate(make_order(symbol="AAPL"), perms, make_context())
        assert result.passed

    def test_fail_blocked(self):
        check = SymbolBlocklistCheck()
        perms = MandatePermissions(blocked_symbols=["GME", "AMC"])
        result = check.evaluate(make_order(symbol="GME"), perms, make_context())
        assert not result.passed
        assert "blocked" in result.reason


# --- AssetTypeCheck ---


class TestAssetTypeCheck:
    def test_pass_when_no_list(self):
        check = AssetTypeCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_allowed(self):
        check = AssetTypeCheck()
        perms = MandatePermissions(allowed_asset_types=["equity"])
        result = check.evaluate(make_order(asset_type=AssetType.EQUITY), perms, make_context())
        assert result.passed

    def test_fail_not_allowed(self):
        check = AssetTypeCheck()
        perms = MandatePermissions(allowed_asset_types=["equity"])
        result = check.evaluate(make_order(asset_type=AssetType.OPTION), perms, make_context())
        assert not result.passed
        assert "not allowed" in result.reason


# --- DailyVolumeCheck ---


class TestDailyVolumeCheck:
    def test_pass_when_no_limit(self):
        check = DailyVolumeCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_within_limit(self):
        check = DailyVolumeCheck()
        perms = MandatePermissions(max_daily_notional_usd=50000)
        result = check.evaluate(make_order(qty=10), perms, make_context(current_price=150))
        assert result.passed

    def test_fail_exceeds_limit(self):
        check = DailyVolumeCheck()
        perms = MandatePermissions(max_daily_notional_usd=50000)
        result = check.evaluate(
            make_order(qty=10),
            perms,
            make_context(current_price=150, daily_notional=49000),
        )
        assert not result.passed
        assert "Daily notional" in result.reason


# --- DailyTradeCountCheck ---


class TestDailyTradeCountCheck:
    def test_pass_when_no_limit(self):
        check = DailyTradeCountCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_within_limit(self):
        check = DailyTradeCountCheck()
        perms = MandatePermissions(max_daily_trades=10)
        result = check.evaluate(make_order(), perms, make_context(daily_trade_count=5))
        assert result.passed

    def test_fail_exceeds_limit(self):
        check = DailyTradeCountCheck()
        perms = MandatePermissions(max_daily_trades=5)
        result = check.evaluate(make_order(), perms, make_context(daily_trade_count=5))
        assert not result.passed
        assert "Already placed 5 trades" in result.reason


# --- TradingHoursCheck ---


class TestTradingHoursCheck:
    def test_pass_when_not_enforced(self):
        check = TradingHoursCheck()
        perms = MandatePermissions(trading_hours_only=False)
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_during_market_hours(self):
        check = TradingHoursCheck()
        perms = MandatePermissions(trading_hours_only=True)
        # 2024-01-15 is a Monday, set to 10:00 ET
        et = ZoneInfo("America/New_York")
        market_time = datetime(2024, 1, 15, 10, 0, tzinfo=et)
        result = check.evaluate(make_order(), perms, make_context(current_time=market_time))
        assert result.passed

    def test_fail_outside_market_hours(self):
        check = TradingHoursCheck()
        perms = MandatePermissions(trading_hours_only=True)
        et = ZoneInfo("America/New_York")
        after_hours = datetime(2024, 1, 15, 17, 0, tzinfo=et)
        result = check.evaluate(make_order(), perms, make_context(current_time=after_hours))
        assert not result.passed
        assert "Outside market hours" in result.reason

    def test_fail_on_weekend(self):
        check = TradingHoursCheck()
        perms = MandatePermissions(trading_hours_only=True)
        et = ZoneInfo("America/New_York")
        saturday = datetime(2024, 1, 13, 10, 0, tzinfo=et)  # Saturday
        result = check.evaluate(make_order(), perms, make_context(current_time=saturday))
        assert not result.passed
        assert "weekdays" in result.reason


# --- OrderTypeCheck ---


class TestOrderTypeCheck:
    def test_pass_when_no_list(self):
        check = OrderTypeCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_allowed(self):
        check = OrderTypeCheck()
        perms = MandatePermissions(allowed_order_types=["market", "limit"])
        result = check.evaluate(make_order(order_type=OrderType.MARKET), perms, make_context())
        assert result.passed

    def test_fail_not_allowed(self):
        check = OrderTypeCheck()
        perms = MandatePermissions(allowed_order_types=["limit"])
        result = check.evaluate(make_order(order_type=OrderType.MARKET), perms, make_context())
        assert not result.passed


# --- SideCheck ---


class TestSideCheck:
    def test_pass_when_no_list(self):
        check = SideCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_allowed(self):
        check = SideCheck()
        perms = MandatePermissions(allowed_sides=["buy", "sell"])
        result = check.evaluate(make_order(side=Side.BUY), perms, make_context())
        assert result.passed

    def test_fail_not_allowed(self):
        check = SideCheck()
        perms = MandatePermissions(allowed_sides=["buy"])
        result = check.evaluate(make_order(side=Side.SHORT), perms, make_context())
        assert not result.passed


# --- PortfolioPercentCheck ---


class TestPortfolioPercentCheck:
    def test_pass_when_no_limit(self):
        check = PortfolioPercentCheck()
        perms = MandatePermissions()
        result = check.evaluate(make_order(), perms, make_context())
        assert result.passed

    def test_pass_within_limit(self):
        check = PortfolioPercentCheck()
        perms = MandatePermissions(max_portfolio_pct_per_order=10)
        # 10 * 150 = 1500, 1.5% of 100k
        result = check.evaluate(make_order(qty=10), perms, make_context(current_price=150))
        assert result.passed

    def test_fail_exceeds_limit(self):
        check = PortfolioPercentCheck()
        perms = MandatePermissions(max_portfolio_pct_per_order=5)
        # 100 * 150 = 15000, 15% of 100k
        result = check.evaluate(make_order(qty=100), perms, make_context(current_price=150))
        assert not result.passed
        assert "portfolio" in result.reason.lower()


# --- MandateEngine ---


class TestMandateEngine:
    def test_all_pass(self):
        mandate = Mandate(
            mandate_id="test",
            permissions=MandatePermissions(
                max_order_size_usd=100000,
                allowed_symbols=["AAPL"],
                allowed_sides=["buy"],
            ),
        )
        engine = MandateEngine(mandate)
        result = engine.evaluate(make_order(symbol="AAPL", qty=10, side=Side.BUY), make_context())
        assert result.passed
        assert result.blocked_reason is None

    def test_one_fails(self):
        mandate = Mandate(
            mandate_id="test",
            permissions=MandatePermissions(
                max_order_size_usd=100,
                allowed_symbols=["AAPL"],
            ),
        )
        engine = MandateEngine(mandate)
        # 10 * 150 = 1500 > 100
        result = engine.evaluate(make_order(qty=10), make_context(current_price=150))
        assert not result.passed
        assert "exceeds max order size" in result.blocked_reason

    def test_multiple_fail(self):
        mandate = Mandate(
            mandate_id="test",
            permissions=MandatePermissions(
                max_order_size_usd=100,
                allowed_symbols=["MSFT"],
                blocked_symbols=["AAPL"],
            ),
        )
        engine = MandateEngine(mandate)
        result = engine.evaluate(make_order(symbol="AAPL", qty=10), make_context(current_price=150))
        assert not result.passed
        failed_checks = [c for c in result.checks if not c.passed]
        assert len(failed_checks) >= 2
