"""Sign and verify mandate files with Ed25519 owner keys."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import yaml
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def _mandate_bytes(raw: dict) -> bytes:
    """Canonical JSON serialization for deterministic signing."""
    return json.dumps(raw, sort_keys=True, default=str).encode()


def _owner_fingerprint(public_key: Ed25519PublicKey) -> str:
    """Return owner:sha256:<hex> fingerprint."""
    raw = public_key.public_bytes_raw()
    return "owner:" + hashlib.sha256(raw).hexdigest()


def sign_mandate(mandate_path: Path, private_key: Ed25519PrivateKey) -> None:
    """Sign a mandate YAML file in-place with the owner's private key.

    Temporarily makes the file writable, writes signature fields, then
    restores read-only (0o444) permissions.
    """
    raw = yaml.safe_load(mandate_path.read_text())

    # Remove existing signature fields before signing
    raw.pop("_signature", None)
    raw.pop("_signed_at", None)
    raw.pop("_signed_by", None)

    mandate_bytes = _mandate_bytes(raw)
    signature = private_key.sign(mandate_bytes)

    # Add signature fields
    raw["_signature"] = "ed25519:" + signature.hex()
    raw["_signed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    raw["_signed_by"] = _owner_fingerprint(private_key.public_key())

    # Temporarily make writable, write, then read-only
    os.chmod(mandate_path, 0o644)
    mandate_path.write_text(yaml.dump(raw, sort_keys=False, default_flow_style=False))
    os.chmod(mandate_path, 0o444)


def verify_mandate_signature(mandate_data: dict, public_key: Ed25519PublicKey) -> bool:
    """Verify a mandate dict's signature against the owner's public key.

    Note: This modifies the input dict by removing signature fields.
    Pass a copy if you need the original preserved.
    """
    signature_hex = mandate_data.pop("_signature", None)
    mandate_data.pop("_signed_at", None)
    mandate_data.pop("_signed_by", None)

    if not signature_hex:
        return False

    signature = bytes.fromhex(signature_hex.replace("ed25519:", ""))
    mandate_bytes = _mandate_bytes(mandate_data)

    try:
        public_key.verify(signature, mandate_bytes)
        return True
    except InvalidSignature:
        return False


def compute_mandate_hash(mandate_path: Path) -> str:
    """Compute sha256 hash of a mandate file's contents."""
    content = mandate_path.read_bytes()
    return "sha256:" + hashlib.sha256(content).hexdigest()
