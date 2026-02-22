"""Load and validate YAML mandate files."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml

from vestbridge.mandate.models import Mandate


def load_mandate(path: Path) -> Mandate:
    """Load a mandate from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Empty mandate file: {path}")

    # Set defaults for auto-generated fields
    if "mandate_id" not in data or not data["mandate_id"]:
        data["mandate_id"] = f"mnd_{uuid.uuid4().hex[:8]}"
    if "created_at" not in data:
        data["created_at"] = datetime.now(UTC)

    return Mandate(**data)


def load_mandate_from_dir(mandates_dir: Path, name: str = "default") -> Mandate:
    """Load a named mandate from the mandates directory."""
    path = mandates_dir / f"{name}.yaml"
    if not path.exists():
        path = mandates_dir / f"{name}.yml"
    if not path.exists():
        raise FileNotFoundError(f"Mandate not found: {path}")
    return load_mandate(path)
