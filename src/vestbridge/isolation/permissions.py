"""File permission management — set and verify permissions on startup."""

import os
import platform
import subprocess
from pathlib import Path

from pydantic import BaseModel


class SecurityCheck(BaseModel):
    name: str
    passed: bool
    detail: str
    critical: bool = False


class PermissionManager:
    """Manages file permissions for VestBridge security-critical files."""

    def __init__(
        self,
        owner_private_key_path: Path | None = None,
        owner_public_key_path: Path | None = None,
        mandate_paths: list[Path] | None = None,
        agents_dir: Path | None = None,
    ):
        self.owner_private_key_path = owner_private_key_path
        self.owner_public_key_path = owner_public_key_path
        self.mandate_paths = mandate_paths or []
        self.agents_dir = agents_dir

    def lock_mandate(self, path: Path) -> None:
        """Make mandate file read-only for all users (0o444)."""
        os.chmod(path, 0o444)

    def lock_private_key(self, path: Path) -> None:
        """Owner-read-only for private key (0o400)."""
        os.chmod(path, 0o400)

    def lock_audit_append_only(self, path: Path) -> bool:
        """Make audit log append-only at OS level.

        Returns True if OS-level append-only was set, False if not supported.
        """
        system = platform.system()
        if system == "Linux":
            try:
                subprocess.run(
                    ["chattr", "+a", str(path)],
                    capture_output=True,
                    check=True,
                )
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
        elif system == "Darwin":
            try:
                subprocess.run(
                    ["chflags", "uappend", str(path)],
                    capture_output=True,
                    check=True,
                )
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False
        return False

    def verify_permissions(self) -> list[SecurityCheck]:
        """Run all permission checks, return results."""
        checks: list[SecurityCheck] = []

        # Check mandate files are read-only
        for mandate_path in self.mandate_paths:
            if not mandate_path.exists():
                checks.append(SecurityCheck(
                    name=f"mandate:{mandate_path.name}",
                    passed=False,
                    detail="file missing",
                    critical=True,
                ))
                continue
            mode = mandate_path.stat().st_mode & 0o777
            checks.append(SecurityCheck(
                name=f"mandate:{mandate_path.name}",
                passed=mode == 0o444,
                detail=f"permissions: {oct(mode)}",
            ))

        # Check private key is owner-read-only
        if self.owner_private_key_path and self.owner_private_key_path.exists():
            mode = self.owner_private_key_path.stat().st_mode & 0o777
            checks.append(SecurityCheck(
                name="owner_private_key",
                passed=mode == 0o400,
                detail=f"permissions: {oct(mode)}",
                critical=True,
            ))

        # Check public key exists
        if self.owner_public_key_path:
            checks.append(SecurityCheck(
                name="owner_public_key",
                passed=self.owner_public_key_path.exists(),
                detail="exists" if self.owner_public_key_path.exists() else "missing",
                critical=True,
            ))

        # Check audit logs exist for all agents
        if self.agents_dir and self.agents_dir.exists():
            for agent_dir in sorted(self.agents_dir.iterdir()):
                if not agent_dir.is_dir():
                    continue
                audit = agent_dir / "audit.jsonl"
                checks.append(SecurityCheck(
                    name=f"audit:{agent_dir.name}",
                    passed=audit.exists(),
                    detail="exists" if audit.exists() else "missing",
                ))

        return checks
