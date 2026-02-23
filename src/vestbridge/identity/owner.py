"""Owner identity — Ed25519 keypair generation, storage, and management."""

import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from vestbridge.config import OWNER_DIR


def generate_keypair() -> Ed25519PrivateKey:
    """Generate a new Ed25519 private key."""
    return Ed25519PrivateKey.generate()


def write_private_key(
    private_key: Ed25519PrivateKey,
    path: Path | None = None,
    password: bytes | None = None,
) -> Path:
    """Write private key to PEM file with owner-read-only permissions (0o400)."""
    path = path or (OWNER_DIR / "private.pem")
    path.parent.mkdir(parents=True, exist_ok=True)

    encryption = BestAvailableEncryption(password) if password else NoEncryption()
    pem_bytes = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    path.write_bytes(pem_bytes)
    path.chmod(0o400)
    return path


def write_public_key(
    public_key: Ed25519PublicKey,
    path: Path | None = None,
) -> Path:
    """Write public key to PEM file."""
    path = path or (OWNER_DIR / "public.pem")
    path.parent.mkdir(parents=True, exist_ok=True)

    pem_bytes = public_key.public_bytes(
        encoding=Encoding.PEM,
        format=PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem_bytes)
    return path


def load_private_key(path: Path | None = None, password: bytes | None = None) -> Ed25519PrivateKey:
    """Load private key from PEM file."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    path = path or (OWNER_DIR / "private.pem")
    if not path.exists():
        raise FileNotFoundError(f"Owner private key not found: {path}")

    key = load_pem_private_key(path.read_bytes(), password=password)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError(f"Expected Ed25519 private key, got {type(key).__name__}")
    return key


def load_public_key(path: Path | None = None) -> Ed25519PublicKey:
    """Load public key from PEM file."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    path = path or (OWNER_DIR / "public.pem")
    if not path.exists():
        raise FileNotFoundError(f"Owner public key not found: {path}")

    key = load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError(f"Expected Ed25519 public key, got {type(key).__name__}")
    return key


def owner_key_fingerprint(public_key: Ed25519PublicKey) -> str:
    """Return sha256 fingerprint of the owner's public key raw bytes."""
    raw = public_key.public_bytes_raw()
    return hashlib.sha256(raw).hexdigest()


def keypair_exists(owner_dir: Path | None = None) -> bool:
    """Check if both owner keys exist."""
    owner_dir = owner_dir or OWNER_DIR
    return (owner_dir / "private.pem").exists() and (owner_dir / "public.pem").exists()


def generate_and_store_keypair(
    owner_dir: Path | None = None,
    password: bytes | None = None,
) -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """Generate a new keypair and write both keys to disk.

    Returns the (private_key, public_key) tuple.
    """
    owner_dir = owner_dir or OWNER_DIR
    private_key = generate_keypair()
    public_key = private_key.public_key()

    write_private_key(private_key, owner_dir / "private.pem", password=password)
    write_public_key(public_key, owner_dir / "public.pem")

    return private_key, public_key
