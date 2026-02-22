"""Audit log hash chain verification."""

import hashlib
import json
from pathlib import Path

from vestbridge.audit.models import AuditEntry, VerificationResult


class AuditVerifier:
    """Verify the integrity of an audit log's hash chain."""

    def verify(self, log_path: Path) -> VerificationResult:
        """Read the entire audit log and verify hash chain integrity.

        Checks:
        1. Each entry's hash matches its contents
        2. Each entry's prev_hash matches the previous entry's hash
        3. First entry's prev_hash is None
        """
        if not log_path.exists():
            return VerificationResult(valid=True, entries_checked=0)

        entries: list[AuditEntry] = []
        with open(log_path) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(AuditEntry.model_validate_json(line))
                except Exception as e:
                    return VerificationResult(
                        valid=False,
                        entries_checked=i,
                        first_error=f"Line {i + 1}: failed to parse entry: {e}",
                    )

        if not entries:
            return VerificationResult(valid=True, entries_checked=0)

        prev_hash: str | None = None

        for i, entry in enumerate(entries):
            # Verify prev_hash chain
            if entry.prev_hash != prev_hash:
                return VerificationResult(
                    valid=False,
                    entries_checked=i + 1,
                    first_error=(
                        f"Entry {i + 1} ({entry.event_id}): prev_hash mismatch. "
                        f"Expected {prev_hash}, got {entry.prev_hash}"
                    ),
                )

            # Verify entry's own hash
            computed_hash = self._compute_hash(entry)
            if entry.entry_hash != computed_hash:
                return VerificationResult(
                    valid=False,
                    entries_checked=i + 1,
                    first_error=(
                        f"Entry {i + 1} ({entry.event_id}): hash mismatch. "
                        f"Expected {computed_hash}, got {entry.entry_hash}"
                    ),
                )

            prev_hash = entry.entry_hash

        return VerificationResult(valid=True, entries_checked=len(entries))

    @staticmethod
    def _compute_hash(entry: AuditEntry) -> str:
        """Recompute an entry's hash for verification."""
        hashable = entry.model_dump(exclude={"entry_hash", "signature"})
        canonical = json.dumps(hashable, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
