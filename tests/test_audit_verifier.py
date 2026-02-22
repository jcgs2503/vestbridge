"""Tests for audit log hash chain verification."""

import json
from pathlib import Path

from vestbridge.audit.logger import AuditLogger
from vestbridge.audit.verifier import AuditVerifier


def test_verify_valid_chain(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    for i in range(10):
        logger.log(agent_id="agt_test", action=f"action_{i}", params={"i": i})

    verifier = AuditVerifier()
    result = verifier.verify(log_path)
    assert result.valid
    assert result.entries_checked == 10


def test_verify_empty_log(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    verifier = AuditVerifier()
    result = verifier.verify(log_path)
    assert result.valid
    assert result.entries_checked == 0


def test_verify_detects_tampered_entry(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log(agent_id="agt_test", action="action_0", params={})
    logger.log(agent_id="agt_test", action="action_1", params={})
    logger.log(agent_id="agt_test", action="action_2", params={})

    # Tamper with the second entry
    lines = log_path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["action"] = "TAMPERED"
    lines[1] = json.dumps(entry)
    log_path.write_text("\n".join(lines) + "\n")

    verifier = AuditVerifier()
    result = verifier.verify(log_path)
    assert not result.valid
    assert "hash mismatch" in result.first_error


def test_verify_detects_broken_chain(tmp_path: Path):
    log_path = tmp_path / "audit.jsonl"
    logger = AuditLogger(log_path)

    logger.log(agent_id="agt_test", action="action_0", params={})
    logger.log(agent_id="agt_test", action="action_1", params={})

    # Break the chain by changing prev_hash on second entry
    lines = log_path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["prev_hash"] = "sha256:0000000000000000"
    # Recompute entry_hash with the bad prev_hash
    import hashlib

    hashable = {k: v for k, v in entry.items() if k not in ("entry_hash", "signature")}
    entry["entry_hash"] = (
        "sha256:"
        + hashlib.sha256(json.dumps(hashable, sort_keys=True, default=str).encode()).hexdigest()
    )
    lines[1] = json.dumps(entry)
    log_path.write_text("\n".join(lines) + "\n")

    verifier = AuditVerifier()
    result = verifier.verify(log_path)
    assert not result.valid
    assert "prev_hash mismatch" in result.first_error
