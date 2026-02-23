"""Global config loading from ~/.vest/."""

from pathlib import Path

from pydantic import BaseModel

VEST_DIR = Path.home() / ".vest"
OWNER_DIR = VEST_DIR / "owner"
MANDATES_DIR = VEST_DIR / "mandates"
AGENTS_DIR = VEST_DIR / "agents"
PAPER_DIR = VEST_DIR / "paper"


class VestConfig(BaseModel):
    default_broker: str = "paper"
    default_agent: str | None = None


def ensure_dirs() -> None:
    """Create the ~/.vest/ directory structure if it doesn't exist."""
    for d in [VEST_DIR, OWNER_DIR, MANDATES_DIR, AGENTS_DIR, PAPER_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def load_config() -> VestConfig:
    """Load config from ~/.vest/config.yaml, or return defaults."""
    ensure_dirs()
    config_path = VEST_DIR / "config.yaml"
    if config_path.exists():
        import yaml

        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return VestConfig(**data)
    return VestConfig()
