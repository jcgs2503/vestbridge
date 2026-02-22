"""vest agent — agent management commands."""

import click

from vestbridge.cli.main import cli
from vestbridge.config import ensure_dirs


@cli.group()
def agent() -> None:
    """Agent management commands."""


@agent.command("list")
def list_cmd() -> None:
    """List all registered agents."""
    from vestbridge.identity.agent import list_agents

    ensure_dirs()
    agents = list_agents()

    if not agents:
        click.echo("No agents registered. Create one with: vest agent create")
        return

    for a in agents:
        click.echo(f"  {a.agent_id}  {a.name:<20}  created: {a.created_at.isoformat()[:10]}")


@agent.command()
@click.option("--name", default="default", help="Agent name")
def create(name: str) -> None:
    """Create a new agent."""
    from vestbridge.identity.agent import create_agent

    ensure_dirs()
    agent_meta = create_agent(name)
    click.echo(f"Created agent: {agent_meta.agent_id} ({agent_meta.name})")
