"""Pydantic models for audit trail entries."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    event_id: str = Field(default_factory=lambda: "")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str
    action: str
    params: dict
    mandate_id: str | None = None
    mandate_hash: str | None = None
    mandate_check: str | None = None
    mandate_reason: str | None = None
    result: dict | None = None
    prev_hash: str | None = None
    entry_hash: str | None = None
    signature: str | None = None


class VerificationResult(BaseModel):
    valid: bool
    entries_checked: int
    first_error: str | None = None
