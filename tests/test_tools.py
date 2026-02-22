"""Integration tests for MCP tools — full order flow with mandate enforcement."""

from pathlib import Path

import pytest
import yaml

from vestbridge import config as vest_config
from vestbridge.server import get_account, get_audit_log, get_quote, place_order


@pytest.fixture(autouse=True)
def isolated_vest_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect ~/.vest/ to a temp dir for test isolation."""
    vest_dir = tmp_path / ".vest"
    vest_dir.mkdir()
    (vest_dir / "mandates").mkdir()
    (vest_dir / "agents").mkdir()
    (vest_dir / "paper").mkdir()

    monkeypatch.setattr(vest_config, "VEST_DIR", vest_dir)
    monkeypatch.setattr(vest_config, "MANDATES_DIR", vest_dir / "mandates")
    monkeypatch.setattr(vest_config, "AGENTS_DIR", vest_dir / "agents")
    monkeypatch.setattr(vest_config, "PAPER_DIR", vest_dir / "paper")

    # Also patch the server module's imports
    from vestbridge import server
    from vestbridge.brokers import paper as paper_mod

    monkeypatch.setattr(server, "MANDATES_DIR", vest_dir / "mandates")
    monkeypatch.setattr(paper_mod, "STATE_FILE", vest_dir / "paper" / "state.json")

    yield vest_dir


def write_mandate(vest_dir: Path, mandate: dict) -> None:
    with open(vest_dir / "mandates" / "default.yaml", "w") as f:
        yaml.dump(mandate, f)


@pytest.mark.asyncio
async def test_get_quote_returns_data(isolated_vest_dir: Path):
    result = await get_quote("AAPL")
    assert result["symbol"] == "AAPL"
    assert result["price"] > 0


@pytest.mark.asyncio
async def test_get_account_returns_data(isolated_vest_dir: Path):
    result = await get_account()
    assert result["cash_balance"] == 100_000.0


@pytest.mark.asyncio
async def test_place_order_no_mandate(isolated_vest_dir: Path):
    """Without a mandate file, orders should execute freely."""
    result = await place_order(symbol="AAPL", qty=10, side="buy")
    assert result["status"] == "filled"


@pytest.mark.asyncio
async def test_place_order_mandate_pass(isolated_vest_dir: Path):
    """Order within mandate limits should pass."""
    write_mandate(
        isolated_vest_dir,
        {
            "permissions": {
                "max_order_size_usd": 100000,
                "allowed_symbols": ["AAPL", "MSFT"],
                "allowed_sides": ["buy", "sell"],
                "allowed_order_types": ["market", "limit"],
                "allowed_asset_types": ["equity"],
            }
        },
    )
    result = await place_order(symbol="AAPL", qty=10, side="buy")
    assert result["status"] == "filled"


@pytest.mark.asyncio
async def test_place_order_mandate_blocks_symbol(isolated_vest_dir: Path):
    """Order for blocked symbol should be rejected."""
    write_mandate(
        isolated_vest_dir,
        {
            "permissions": {
                "blocked_symbols": ["GME", "AMC"],
            }
        },
    )
    result = await place_order(symbol="GME", qty=10, side="buy")
    assert result["status"] == "blocked"
    assert "blocked" in result["reason"].lower()


@pytest.mark.asyncio
async def test_place_order_mandate_blocks_size(isolated_vest_dir: Path):
    """Order exceeding max size should be rejected."""
    write_mandate(
        isolated_vest_dir,
        {
            "permissions": {
                "max_order_size_usd": 100,
            }
        },
    )
    result = await place_order(symbol="AAPL", qty=1000, side="buy")
    assert result["status"] == "blocked"
    assert "exceeds" in result["reason"].lower()


@pytest.mark.asyncio
async def test_audit_log_records_actions(isolated_vest_dir: Path):
    """Actions should appear in the audit log."""
    await get_quote("AAPL")
    await get_quote("MSFT")

    log = await get_audit_log(n=10)
    assert len(log) >= 2
    actions = [e["action"] for e in log]
    assert "get_quote" in actions


@pytest.mark.asyncio
async def test_blocked_order_appears_in_audit(isolated_vest_dir: Path):
    """Blocked orders should be logged to audit trail."""
    write_mandate(
        isolated_vest_dir,
        {
            "permissions": {
                "blocked_symbols": ["GME"],
            }
        },
    )
    await place_order(symbol="GME", qty=10, side="buy")

    log = await get_audit_log(n=10)
    order_entries = [e for e in log if e["action"] == "place_order"]
    assert len(order_entries) >= 1
    assert order_entries[-1]["mandate_check"] == "FAIL"
