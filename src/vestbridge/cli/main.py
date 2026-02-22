"""Click CLI group for VestBridge."""

import click


@click.group()
@click.version_option(package_name="vestbridge")
def cli() -> None:
    """VestBridge — AI agent trading with mandate enforcement and audit trails."""
