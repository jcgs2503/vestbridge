"""vest mandate — mandate management commands."""

from pathlib import Path

import click

from vestbridge.cli.main import cli


@cli.group()
def mandate() -> None:
    """Mandate management commands."""


@mandate.command()
@click.option("--mandate", "mandate_path", required=True, help="Path to mandate YAML file")
def check(mandate_path: str) -> None:
    """Validate a mandate YAML file."""
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
