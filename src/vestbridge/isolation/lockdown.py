"""Lockdown utilities — apply security hardening on startup."""

from pathlib import Path

from vestbridge.isolation.permissions import PermissionManager, SecurityCheck


def lockdown_vest_dir(
    owner_private_key_path: Path,
    owner_public_key_path: Path,
    mandate_paths: list[Path],
    agents_dir: Path,
) -> list[SecurityCheck]:
    """Apply and verify all security permissions on the ~/.vest/ directory.

    This is called during `vestbridge serve` startup to ensure all files
    have correct permissions before the MCP server starts.

    Returns the list of security check results.
    """
    pm = PermissionManager(
        owner_private_key_path=owner_private_key_path,
        owner_public_key_path=owner_public_key_path,
        mandate_paths=mandate_paths,
        agents_dir=agents_dir,
    )

    # Ensure private key permissions
    if owner_private_key_path.exists():
        mode = owner_private_key_path.stat().st_mode & 0o777
        if mode != 0o400:
            pm.lock_private_key(owner_private_key_path)

    # Ensure mandate permissions
    for mandate_path in mandate_paths:
        if mandate_path.exists():
            mode = mandate_path.stat().st_mode & 0o777
            if mode != 0o444:
                pm.lock_mandate(mandate_path)

    # Ensure audit logs exist and try to set append-only
    if agents_dir.exists():
        for agent_dir in agents_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            audit_path = agent_dir / "audit.jsonl"
            if not audit_path.exists():
                audit_path.touch()
            pm.lock_audit_append_only(audit_path)

    # Verify everything
    return pm.verify_permissions()
