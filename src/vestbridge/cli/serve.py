"""vest serve — start MCP server."""

import click

from vestbridge.cli.main import cli


@cli.command()
@click.option("--broker", default="paper", help="Broker adapter to use")
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
@click.option("--port", default=8080, type=int, help="Port for SSE transport")
def serve(broker: str, transport: str, port: int) -> None:
    """Start the VestBridge MCP server."""
    from vestbridge.config import ensure_dirs

    ensure_dirs()

    if broker != "paper":
        click.echo(f"Broker '{broker}' is not yet supported. Using 'paper'.")

    from vestbridge.server import mcp as mcp_server

    if transport == "sse":
        mcp_server.settings.port = port
        mcp_server.run(transport="sse")
    else:
        mcp_server.run(transport="stdio")
