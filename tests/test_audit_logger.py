"""Tests for audit logger hash chain."""

from pathlib import Path

from vestbridge.audit.logger import AuditLogger


def test_log_creates_hash_chain(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    e1 = logger.log(agent_id="agt_test", action="get_quote", params={"symbol": "AAPL"})
    assert e1.prev_hash is None
    assert e1.entry_hash is not None
    assert e1.entry_hash.startswith("sha256:")

    e2 = logger.log(agent_id="agt_test", action="get_quote", params={"symbol": "MSFT"})
    assert e2.prev_hash == e1.entry_hash
    assert e2.entry_hash != e1.entry_hash

    e3 = logger.log(agent_id="agt_test", action="place_order", params={"symbol": "GOOG"})
    assert e3.prev_hash == e2.entry_hash


def test_log_persists_to_file(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log(agent_id="agt_test", action="test1", params={})
    logger.log(agent_id="agt_test", action="test2", params={})

    entries = logger.read_entries()
    assert len(entries) == 2
    assert entries[0].action == "test1"
    assert entries[1].action == "test2"


def test_read_last_n(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    for i in range(5):
        logger.log(agent_id="agt_test", action=f"action_{i}", params={})

    last_2 = logger.read_entries(last_n=2)
    assert len(last_2) == 2
    assert last_2[0].action == "action_3"
    assert last_2[1].action == "action_4"


def test_logger_resumes_hash_chain(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"

    # First session
    logger1 = AuditLogger(log_path)
    e1 = logger1.log(agent_id="agt_test", action="first", params={})

    # New session — should pick up where we left off
    logger2 = AuditLogger(log_path)
    e2 = logger2.log(agent_id="agt_test", action="second", params={})
    assert e2.prev_hash == e1.entry_hash


def test_mandate_check_fields(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    entry = logger.log(
        agent_id="agt_test",
        action="place_order",
        params={"symbol": "NVDA", "qty": 100},
        mandate_id="mnd_abc123",
        mandate_check="FAIL",
        mandate_reason="exceeds max concentration",
    )
    assert entry.mandate_check == "FAIL"
    assert entry.mandate_reason == "exceeds max concentration"
    assert entry.mandate_id == "mnd_abc123"
