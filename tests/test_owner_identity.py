"""Tests for owner identity — keypair generation, storage, loading."""

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from vestbridge.identity.owner import (
    generate_and_store_keypair,
    generate_keypair,
    keypair_exists,
    load_private_key,
    load_public_key,
    owner_key_fingerprint,
    write_private_key,
    write_public_key,
)


class TestKeypairGeneration:
    def test_generate_keypair_returns_private_key(self):
        key = generate_keypair()
        assert isinstance(key, Ed25519PrivateKey)

    def test_generated_keys_are_unique(self):
        k1 = generate_keypair()
        k2 = generate_keypair()
        assert k1.public_key().public_bytes_raw() != k2.public_key().public_bytes_raw()


class TestKeyStorage:
    def test_write_and_load_private_key(self, tmp_path: Path):
        key = generate_keypair()
        path = tmp_path / "private.pem"
        write_private_key(key, path)

        loaded = load_private_key(path)
        assert isinstance(loaded, Ed25519PrivateKey)
        # Verify they produce same public key
        assert key.public_key().public_bytes_raw() == loaded.public_key().public_bytes_raw()

    def test_private_key_permissions(self, tmp_path: Path):
        key = generate_keypair()
        path = tmp_path / "private.pem"
        write_private_key(key, path)

        mode = path.stat().st_mode & 0o777
        assert mode == 0o400

    def test_write_and_load_public_key(self, tmp_path: Path):
        key = generate_keypair()
        pub = key.public_key()
        path = tmp_path / "public.pem"
        write_public_key(pub, path)

        loaded = load_public_key(path)
        assert isinstance(loaded, Ed25519PublicKey)
        assert pub.public_bytes_raw() == loaded.public_bytes_raw()

    def test_load_missing_private_key_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_private_key(tmp_path / "nonexistent.pem")

    def test_load_missing_public_key_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_public_key(tmp_path / "nonexistent.pem")

    def test_write_private_key_with_password(self, tmp_path: Path):
        key = generate_keypair()
        path = tmp_path / "private.pem"
        password = b"test-password"
        write_private_key(key, path, password=password)

        loaded = load_private_key(path, password=password)
        assert key.public_key().public_bytes_raw() == loaded.public_key().public_bytes_raw()

    def test_write_private_key_creates_parent_dirs(self, tmp_path: Path):
        key = generate_keypair()
        path = tmp_path / "nested" / "dir" / "private.pem"
        write_private_key(key, path)
        assert path.exists()


class TestGenerateAndStore:
    def test_generate_and_store_creates_both_files(self, tmp_path: Path):
        owner_dir = tmp_path / "owner"
        private_key, public_key = generate_and_store_keypair(owner_dir)

        assert (owner_dir / "private.pem").exists()
        assert (owner_dir / "public.pem").exists()
        assert isinstance(private_key, Ed25519PrivateKey)
        assert isinstance(public_key, Ed25519PublicKey)

    def test_round_trip(self, tmp_path: Path):
        owner_dir = tmp_path / "owner"
        private_key, public_key = generate_and_store_keypair(owner_dir)

        loaded_priv = load_private_key(owner_dir / "private.pem")
        loaded_pub = load_public_key(owner_dir / "public.pem")

        orig_raw = private_key.public_key().public_bytes_raw()
        assert orig_raw == loaded_priv.public_key().public_bytes_raw()
        assert public_key.public_bytes_raw() == loaded_pub.public_bytes_raw()


class TestFingerprint:
    def test_fingerprint_is_hex_sha256(self):
        key = generate_keypair()
        fp = owner_key_fingerprint(key.public_key())
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)

    def test_same_key_same_fingerprint(self):
        key = generate_keypair()
        fp1 = owner_key_fingerprint(key.public_key())
        fp2 = owner_key_fingerprint(key.public_key())
        assert fp1 == fp2

    def test_different_keys_different_fingerprints(self):
        k1 = generate_keypair()
        k2 = generate_keypair()
        assert owner_key_fingerprint(k1.public_key()) != owner_key_fingerprint(k2.public_key())


class TestKeypairExists:
    def test_exists_when_both_present(self, tmp_path: Path):
        owner_dir = tmp_path / "owner"
        generate_and_store_keypair(owner_dir)
        assert keypair_exists(owner_dir)

    def test_not_exists_when_empty(self, tmp_path: Path):
        assert not keypair_exists(tmp_path)

    def test_not_exists_when_only_public(self, tmp_path: Path):
        owner_dir = tmp_path / "owner"
        owner_dir.mkdir()
        key = generate_keypair()
        write_public_key(key.public_key(), owner_dir / "public.pem")
        assert not keypair_exists(owner_dir)
