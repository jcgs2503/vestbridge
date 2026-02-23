"""vest mandate — mandate management commands."""

from pathlib import Path

import click
import yaml

from vestbridge.cli.main import cli
from vestbridge.config import MANDATES_DIR, OWNER_DIR


@cli.group()
def mandate() -> None:
    """Mandate management commands."""


@mandate.command()
@click.argument("path", required=False, type=click.Path(exists=True))
def sign(path: str | None) -> None:
    """Sign a mandate YAML file with the owner's private key."""
    from vestbridge.identity.owner import load_private_key
    from vestbridge.mandate.signer import sign_mandate

    mandate_path = Path(path) if path else MANDATES_DIR / "default.yaml"
    if not mandate_path.exists():
        click.echo(f"Mandate not found: {mandate_path}")
        raise SystemExit(1)

    try:
        private_key = load_private_key(OWNER_DIR / "private.pem")
    except FileNotFoundError:
        click.echo("Owner private key not found. Run 'vestbridge init' first.")
        raise SystemExit(1)

    sign_mandate(mandate_path, private_key)
    click.echo("  ✓ Mandate signed with owner key")
    click.echo("  ✓ File set to read-only (444)")


@mandate.command()
@click.argument("path", required=False, type=click.Path(exists=True))
def verify(path: str | None) -> None:
    """Verify a mandate's signature against the owner's public key."""
    from vestbridge.identity.owner import load_public_key
    from vestbridge.mandate.signer import verify_mandate_signature

    mandate_path = Path(path) if path else MANDATES_DIR / "default.yaml"
    if not mandate_path.exists():
        click.echo(f"Mandate not found: {mandate_path}")
        raise SystemExit(1)

    try:
        public_key = load_public_key(OWNER_DIR / "public.pem")
    except FileNotFoundError:
        click.echo("Owner public key not found. Run 'vestbridge init' first.")
        raise SystemExit(1)

    data = yaml.safe_load(mandate_path.read_text())
    signed_at = data.get("_signed_at", "unknown")
    signed_by = data.get("_signed_by", "unknown")

    if verify_mandate_signature(data.copy(), public_key):
        click.echo("  ✓ Signature valid")
        click.echo(f"  ✓ Signed at: {signed_at}")
        click.echo(f"  ✓ Signed by: {signed_by}")
    else:
        click.echo("  ✗ SIGNATURE INVALID — POSSIBLE TAMPERING")
        click.echo(f"  Re-sign with: vestbridge mandate sign {mandate_path}")
        raise SystemExit(1)


@mandate.command()
@click.argument("path", required=False, type=click.Path(exists=True))
def show(path: str | None) -> None:
    """Display mandate contents and status."""
    mandate_path = Path(path) if path else MANDATES_DIR / "default.yaml"
    if not mandate_path.exists():
        click.echo(f"Mandate not found: {mandate_path}")
        raise SystemExit(1)

    data = yaml.safe_load(mandate_path.read_text())
    p = data.get("permissions", {})

    click.echo(f"  Mandate: {data.get('mandate_id', 'unknown')} (v{data.get('version', '?')})")
    click.echo(f"  Scope: {data.get('scope', 'unknown')}")

    if p.get("max_order_size_usd"):
        click.echo(f"  Max order size: ${p['max_order_size_usd']:,.0f}")
    if p.get("max_daily_notional_usd"):
        click.echo(f"  Max daily notional: ${p['max_daily_notional_usd']:,.0f}")
    if p.get("max_daily_trades"):
        click.echo(f"  Max daily trades: {p['max_daily_trades']}")
    if p.get("max_concentration_pct"):
        click.echo(f"  Concentration limit: {p['max_concentration_pct']}%")
    if p.get("allowed_asset_types"):
        click.echo(f"  Allowed assets: {', '.join(p['allowed_asset_types'])}")
    if p.get("blocked_symbols"):
        click.echo(f"  Blocked symbols: {', '.join(p['blocked_symbols'])}")
    if p.get("allowed_symbols"):
        click.echo(f"  Allowed symbols: {', '.join(p['allowed_symbols'])}")

    # Status
    has_sig = "_signature" in data
    mode = oct(mandate_path.stat().st_mode & 0o777)
    is_readonly = mode == "0o444"
    status_parts = []
    if has_sig:
        status_parts.append("signed")
    else:
        status_parts.append("unsigned")
    if is_readonly:
        status_parts.append("read-only")
    else:
        status_parts.append(f"writable ({mode})")

    icon = "✓" if has_sig and is_readonly else "⚠"
    click.echo(f"  Status: {icon} {', '.join(status_parts)}")


@mandate.command()
@click.option("--mandate", "mandate_path", required=True, help="Path to mandate YAML file")
def check(mandate_path: str) -> None:
    """Validate a mandate YAML file (legacy command)."""
    from vestbridge.mandate.loader import load_mandate

    path = Path(mandate_path)
    if not path.exists():
        click.echo(f"File not found: {mandate_path}")
        raise SystemExit(1)

    try:
        m = load_mandate(path)
        click.echo(f"Mandate is valid: {m.mandate_id}")
        p = m.permissions
        if p.allowed_symbols:
            click.echo(f"  allowed symbols: {', '.join(p.allowed_symbols)}")
        if p.blocked_symbols:
            click.echo(f"  blocked symbols: {', '.join(p.blocked_symbols)}")
        if p.max_order_size_usd:
            click.echo(f"  max order size: ${p.max_order_size_usd:,.0f}")
        if p.max_daily_notional_usd:
            click.echo(f"  max daily notional: ${p.max_daily_notional_usd:,.0f}")
        if p.max_concentration_pct:
            click.echo(f"  max concentration: {p.max_concentration_pct}%")
    except Exception as e:
        click.echo(f"Invalid mandate: {e}")
        raise SystemExit(1)
