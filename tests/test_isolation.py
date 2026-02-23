"""Tests for isolation module — file permissions and lockdown."""

import os
from pathlib import Path

from vestbridge.isolation.lockdown import lockdown_vest_dir
from vestbridge.isolation.permissions import PermissionManager


class TestPermissionManager:
    def _setup_dirs(self, tmp_path: Path) -> dict:
        owner_dir = tmp_path / "owner"
        owner_dir.mkdir()
        priv = owner_dir / "private.pem"
        pub = owner_dir / "public.pem"
        priv.write_text("fake-private-key")
        pub.write_text("fake-public-key")

        mandates_dir = tmp_path / "mandates"
        mandates_dir.mkdir()
        mandate = mandates_dir / "default.yaml"
        mandate.write_text("permissions: {}")

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_dir = agents_dir / "agt_test1234"
        agent_dir.mkdir()
        (agent_dir / "audit.jsonl").touch()

        return {
            "priv": priv,
            "pub": pub,
            "mandate": mandate,
            "agents_dir": agents_dir,
        }

    def test_lock_mandate_sets_444(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        pm = PermissionManager()
        pm.lock_mandate(d["mandate"])
        mode = d["mandate"].stat().st_mode & 0o777
        assert mode == 0o444

    def test_lock_private_key_sets_400(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        pm = PermissionManager()
        pm.lock_private_key(d["priv"])
        mode = d["priv"].stat().st_mode & 0o777
        assert mode == 0o400

    def test_verify_permissions_all_pass(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        os.chmod(d["priv"], 0o400)
        os.chmod(d["mandate"], 0o444)

        pm = PermissionManager(
            owner_private_key_path=d["priv"],
            owner_public_key_path=d["pub"],
            mandate_paths=[d["mandate"]],
            agents_dir=d["agents_dir"],
        )
        checks = pm.verify_permissions()
        assert all(c.passed for c in checks)

    def test_verify_detects_writable_mandate(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        os.chmod(d["priv"], 0o400)
        os.chmod(d["mandate"], 0o644)

        pm = PermissionManager(
            owner_private_key_path=d["priv"],
            owner_public_key_path=d["pub"],
            mandate_paths=[d["mandate"]],
            agents_dir=d["agents_dir"],
        )
        checks = pm.verify_permissions()
        mandate_check = next(c for c in checks if "mandate" in c.name)
        assert not mandate_check.passed

    def test_verify_detects_loose_private_key(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        os.chmod(d["priv"], 0o644)
        os.chmod(d["mandate"], 0o444)

        pm = PermissionManager(
            owner_private_key_path=d["priv"],
            owner_public_key_path=d["pub"],
            mandate_paths=[d["mandate"]],
            agents_dir=d["agents_dir"],
        )
        checks = pm.verify_permissions()
        key_check = next(c for c in checks if c.name == "owner_private_key")
        assert not key_check.passed

    def test_verify_detects_missing_public_key(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        d["pub"].unlink()

        pm = PermissionManager(
            owner_private_key_path=d["priv"],
            owner_public_key_path=d["pub"],
            mandate_paths=[],
            agents_dir=d["agents_dir"],
        )
        checks = pm.verify_permissions()
        pub_check = next(c for c in checks if c.name == "owner_public_key")
        assert not pub_check.passed

    def test_verify_detects_missing_audit_log(self, tmp_path: Path):
        d = self._setup_dirs(tmp_path)
        audit = d["agents_dir"] / "agt_test1234" / "audit.jsonl"
        audit.unlink()

        pm = PermissionManager(
            owner_private_key_path=d["priv"],
            owner_public_key_path=d["pub"],
            mandate_paths=[],
            agents_dir=d["agents_dir"],
        )
        checks = pm.verify_permissions()
        audit_check = next(c for c in checks if "audit" in c.name)
        assert not audit_check.passed

    def test_verify_missing_mandate_file(self, tmp_path: Path):
        pm = PermissionManager(
            mandate_paths=[tmp_path / "nonexistent.yaml"],
        )
        checks = pm.verify_permissions()
        assert len(checks) == 1
        assert not checks[0].passed
        assert checks[0].critical


class TestLockdown:
    def test_lockdown_fixes_permissions(self, tmp_path: Path):
        # Setup with bad permissions
        owner_dir = tmp_path / "owner"
        owner_dir.mkdir()
        priv = owner_dir / "private.pem"
        pub = owner_dir / "public.pem"
        priv.write_text("key")
        pub.write_text("key")
        os.chmod(priv, 0o644)  # too permissive

        mandates_dir = tmp_path / "mandates"
        mandates_dir.mkdir()
        mandate = mandates_dir / "default.yaml"
        mandate.write_text("test")
        os.chmod(mandate, 0o755)  # too permissive

        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        agent_dir = agents_dir / "agt_abc12345"
        agent_dir.mkdir()
        # Don't create audit.jsonl — lockdown should create it

        checks = lockdown_vest_dir(priv, pub, [mandate], agents_dir)

        # Private key should now be 0o400
        assert priv.stat().st_mode & 0o777 == 0o400
        # Mandate should now be 0o444
        assert mandate.stat().st_mode & 0o777 == 0o444
        # Audit log should exist now
        assert (agent_dir / "audit.jsonl").exists()
        # All checks should pass
        assert all(c.passed for c in checks)
