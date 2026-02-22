"""Append-only JSONL audit logger with hash chain."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from vestbridge.audit.models import AuditEntry


class AuditLogger:
    """Append-only JSONL logger with hash chain.

    Each entry's prev_hash points to the previous entry's hash,
    forming an integrity-verifiable chain.
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._last_hash = self._read_last_hash()

    def log(
        self,
        agent_id: str,
        action: str,
        params: dict,
        mandate_id: str | None = None,
        mandate_hash: str | None = None,
        mandate_check: str | None = None,
        mandate_reason: str | None = None,
        result: dict | None = None,
    ) -> AuditEntry:
        """Create and append an audit entry to the log."""
        entry = AuditEntry(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(UTC),
            agent_id=agent_id,
            action=action,
            params=params,
            mandate_id=mandate_id,
            mandate_hash=mandate_hash,
            mandate_check=mandate_check,
            mandate_reason=mandate_reason,
            result=result,
            prev_hash=self._last_hash,
        )
        entry.entry_hash = self._compute_hash(entry)
        self._last_hash = entry.entry_hash

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry

    def read_entries(self, last_n: int | None = None) -> list[AuditEntry]:
        """Read entries from the audit log."""
        if not self.log_path.exists():
            return []

        entries = []
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(AuditEntry.model_validate_json(line))

        if last_n is not None:
            return entries[-last_n:]
        return entries

    def get_daily_stats(self, agent_id: str) -> tuple[float, int]:
        """Get today's total notional traded and trade count for an agent.

        Returns (daily_notional, daily_trade_count).
        """
        today = datetime.now(UTC).date()
        daily_notional = 0.0
        daily_trade_count = 0

        entries = self.read_entries()
        for entry in entries:
            if entry.agent_id != agent_id:
                continue
            if entry.timestamp.date() != today:
                continue
            if entry.action != "place_order":
                continue
            if entry.mandate_check != "PASS":
                continue

            # Extract notional from result
            if entry.result and "filled_price" in entry.result and "qty" in entry.params:
                daily_notional += entry.result["filled_price"] * entry.params["qty"]
            daily_trade_count += 1

        return daily_notional, daily_trade_count

    @staticmethod
    def _compute_hash(entry: AuditEntry) -> str:
        """Hash everything except entry_hash and signature."""
        hashable = entry.model_dump(exclude={"entry_hash", "signature"})
        canonical = json.dumps(hashable, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    def _read_last_hash(self) -> str | None:
        """Read the last entry's hash from the log file, or None if empty."""
        if not self.log_path.exists():
            return None

        last_line = None
        with open(self.log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line

        if last_line is None:
            return None

        entry = AuditEntry.model_validate_json(last_line)
        return entry.entry_hash
