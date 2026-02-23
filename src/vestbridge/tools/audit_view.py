"""get_recent_actions tool — limited audit view for the agent."""

from vestbridge.audit.logger import AuditLogger


def handle_get_recent_actions(
    *,
    audit_logger: AuditLogger,
    agent_id: str,
    n: int = 10,
) -> list[dict]:
    """Return summary of last N actions for the agent.

    The agent sees: action, timestamp, pass/fail, reason.
    The agent does NOT see: full hash chain, mandate hashes, internal metadata.
    """
    entries = audit_logger.read_entries(last_n=n)
    summaries = []
    for entry in entries:
        summary = {
            "action": entry.action,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "params": entry.params,
        }
        if entry.mandate_check:
            summary["mandate_check"] = entry.mandate_check
        if entry.mandate_reason:
            summary["mandate_reason"] = entry.mandate_reason
        if entry.result:
            summary["status"] = entry.result.get("status", "ok")
        summaries.append(summary)
    return summaries
