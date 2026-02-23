"""vestbridge init — interactive setup wizard."""

import os
import uuid
from datetime import UTC, datetime

import click
import yaml

from vestbridge.cli.main import cli
from vestbridge.config import AGENTS_DIR, MANDATES_DIR, OWNER_DIR, VEST_DIR


@cli.command()
def init() -> None:
    """Set up VestBridge: generate keys, create mandate, initialize agent."""
    click.echo()
    click.echo("VestBridge Setup")
    click.echo("================")
    click.echo()

    # 1. Create directory structure
    for d in [VEST_DIR, OWNER_DIR, MANDATES_DIR, AGENTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Generate owner keypair
    _setup_owner_keys()

    # 3. Create mandate interactively
    _create_mandate()

    # 4. Create default agent
    _create_default_agent()

    click.echo()
    click.echo("Ready. Start with: vestbridge serve --broker paper")


def _setup_owner_keys() -> None:
    """Generate owner Ed25519 keypair."""
    from vestbridge.identity.owner import generate_and_store_keypair, keypair_exists

    click.echo("Generating owner keypair...")

    if keypair_exists(OWNER_DIR):
        click.echo(f"  Keypair already exists at {OWNER_DIR}")
        if not click.confirm("  Overwrite existing keypair?", default=False):
            click.echo("  Keeping existing keypair.")
            return

    generate_and_store_keypair(OWNER_DIR)
    click.echo(f"  ✓ Private key: {OWNER_DIR / 'private.pem'} (owner-read only)")
    click.echo(f"  ✓ Public key:  {OWNER_DIR / 'public.pem'}")
    click.echo()


def _create_mandate() -> None:
    """Create and sign a default mandate from user prompts."""
    from vestbridge.identity.owner import load_private_key
    from vestbridge.mandate.signer import sign_mandate

    click.echo("Creating default mandate...")

    max_order = click.prompt("  Max order size (USD)", default=10000, type=float)
    max_concentration = click.prompt("  Max single-stock concentration (%)", default=20, type=float)
    max_daily_notional = click.prompt("  Max daily notional (USD)", default=50000, type=float)
    max_daily_trades = click.prompt("  Max daily trades", default=50, type=int)
    asset_types_str = click.prompt("  Allowed asset types", default="equity")
    blocked_str = click.prompt("  Block any symbols?", default="")
    allowed_str = click.prompt("  Restrict to specific symbols? (leave blank for all)", default="")

    allowed_types = [t.strip() for t in asset_types_str.split(",") if t.strip()]
    blocked = [s.strip().upper() for s in blocked_str.split(",") if s.strip()] or None
    allowed = [s.strip().upper() for s in allowed_str.split(",") if s.strip()] or None

    mandate_data = {
        "mandate_id": f"mdt_{uuid.uuid4().hex[:8]}",
        "version": 1,
        "scope": "agent",
        "description": "Default mandate created by vestbridge init",
        "permissions": {
            "max_order_size_usd": max_order,
            "max_daily_notional_usd": max_daily_notional,
            "max_daily_trades": max_daily_trades,
            "allowed_symbols": allowed,
            "blocked_symbols": blocked,
            "allowed_sides": ["buy", "sell"],
            "allowed_order_types": ["market", "limit"],
            "allowed_asset_types": allowed_types,
            "max_concentration_pct": max_concentration,
            "max_portfolio_pct_per_order": 10,
            "trading_hours_only": True,
            "require_limit_orders": False,
        },
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    mandate_path = MANDATES_DIR / "default.yaml"
    # Make writable if it exists and is read-only
    if mandate_path.exists():
        os.chmod(mandate_path, 0o644)
    mandate_path.write_text(yaml.dump(mandate_data, sort_keys=False, default_flow_style=False))

    click.echo(f"  ✓ Mandate written to {mandate_path}")

    # Sign the mandate
    try:
        private_key = load_private_key(OWNER_DIR / "private.pem")
        sign_mandate(mandate_path, private_key)
        click.echo("  ✓ Mandate signed with owner key")
        click.echo("  ✓ Mandate file set to read-only")
    except FileNotFoundError:
        click.echo("  ⚠ Could not sign mandate (no private key found)")
        os.chmod(mandate_path, 0o444)

    click.echo()


def _create_default_agent() -> None:
    """Create a default agent with initialized audit log."""
    from vestbridge.identity.agent import create_agent, list_agents

    click.echo("Creating default agent...")

    existing = list_agents(AGENTS_DIR)
    if existing:
        click.echo(f"  Agent already exists: {existing[0].agent_id} ({existing[0].name})")
        if not click.confirm("  Create another agent?", default=False):
            click.echo(f"  ✓ Using existing agent {existing[0].agent_id}")
            return

    name = click.prompt("  Agent name", default="default")
    agent = create_agent(name, AGENTS_DIR)

    # Initialize empty audit log
    audit_path = AGENTS_DIR / agent.agent_id / "audit.jsonl"
    if not audit_path.exists():
        audit_path.touch()

    click.echo(f"  ✓ Agent {agent.agent_id} created")
    click.echo("  ✓ Audit log initialized")
    click.echo()
