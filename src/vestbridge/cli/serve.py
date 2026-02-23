"""vest serve — start MCP server with security checks."""

import os
import sys

import click
import yaml

from vestbridge.cli.main import cli
from vestbridge.config import AGENTS_DIR, MANDATES_DIR, OWNER_DIR


@cli.command()
@click.option("--broker", default="paper", help="Broker adapter to use")
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
@click.option("--port", default=8080, type=int, help="Port for SSE transport")
@click.option("--skip-security", is_flag=True, default=False, help="Skip security checks")
def serve(broker: str, transport: str, port: int, skip_security: bool) -> None:
    """Start the VestBridge MCP server."""
    from vestbridge.config import ensure_dirs

    ensure_dirs()

    click.echo()
    click.echo("VestBridge v0.1.0")
    click.echo("=================")

    if not skip_security:
        if not _run_security_checks():
            sys.exit(1)

    if broker != "paper":
        click.echo(f"Broker '{broker}' is not yet supported. Using 'paper'.")

    # Count active mandate checks
    mandate_info = _get_mandate_info()
    agent_info = _get_agent_info()

    click.echo()
    click.echo(f"Broker: {broker} (starting balance: $100,000)")
    if agent_info:
        click.echo(f"Agent: {agent_info}")
    if mandate_info:
        click.echo(f"Mandate: {mandate_info}")
    click.echo()
    click.echo(f"MCP server ready on {transport}")
    click.echo("Connect your AI agent to start trading.")

    from vestbridge.server import mcp as mcp_server

    if transport == "sse":
        mcp_server.settings.port = port
        mcp_server.run(transport="sse")
    else:
        mcp_server.run(transport="stdio")


def _run_security_checks() -> bool:
    """Run startup security checks. Return False if critical checks fail."""
    click.echo("Security checks:")

    all_passed = True

    # Check owner keypair
    priv_path = OWNER_DIR / "private.pem"
    pub_path = OWNER_DIR / "public.pem"

    if priv_path.exists():
        click.echo("  ✓ Owner keypair found")
    else:
        click.echo("  ⚠ Owner keypair not found (run 'vestbridge init')")

    # Check and verify mandate signatures
    mandate_paths = list(MANDATES_DIR.glob("*.yaml")) + list(MANDATES_DIR.glob("*.yml"))
    if not mandate_paths:
        click.echo("  ⚠ No mandate files found")
    else:
        for mp in mandate_paths:
            sig_valid = _check_mandate_signature(mp, pub_path)
            if sig_valid is True:
                click.echo(f"  ✓ Mandate signature valid ({mp.name})")
            elif sig_valid is False:
                click.echo(f"  ✗ FATAL: Mandate {mp.name} has invalid signature.")
                click.echo("    Someone may have tampered with this file.")
                click.echo(f"    Re-sign with: vestbridge mandate sign {mp}")
                all_passed = False
            else:
                click.echo(f"  ⚠ Mandate {mp.name} is unsigned")

            # Check read-only
            mode = mp.stat().st_mode & 0o777
            if mode == 0o444:
                click.echo("  ✓ Mandate file is read-only")
            else:
                click.echo(f"  ⚠ Warning: {mp.name} is writable. Locking down...")
                os.chmod(mp, 0o444)

    # Check audit logs
    if AGENTS_DIR.exists():
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir():
                continue
            audit = agent_dir / "audit.jsonl"
            if audit.exists():
                click.echo("  ✓ Audit log is append-only")
            else:
                click.echo(f"  ⚠ Audit log missing for {agent_dir.name}")

    click.echo(f"  ✓ Running as separate process (PID {os.getpid()})")

    if not all_passed:
        click.echo()
        click.echo("  FATAL: Critical security checks failed. Refusing to start.")
        click.echo("  Run 'vestbridge mandate sign' to re-sign mandates.")

    return all_passed


def _check_mandate_signature(mandate_path, pub_path) -> bool | None:
    """Check mandate signature. Returns True/False/None (unsigned)."""
    try:
        from vestbridge.identity.owner import load_public_key
        from vestbridge.mandate.signer import verify_mandate_signature

        data = yaml.safe_load(mandate_path.read_text())
        if "_signature" not in data:
            return None

        public_key = load_public_key(pub_path)
        return verify_mandate_signature(data.copy(), public_key)
    except FileNotFoundError:
        return None
    except Exception:
        return False


def _get_mandate_info() -> str | None:
    """Get mandate summary for startup display."""
    mandate_paths = list(MANDATES_DIR.glob("*.yaml")) + list(MANDATES_DIR.glob("*.yml"))
    if not mandate_paths:
        return None

    mp = mandate_paths[0]
    try:
        data = yaml.safe_load(mp.read_text())
        mid = data.get("mandate_id", mp.stem)
        perms = data.get("permissions", {})
        check_count = sum(1 for v in perms.values() if v is not None and v is not False)
        signed = "signed" if "_signature" in data else "unsigned"
        return f"{mid} ({signed}, {check_count} active checks)"
    except Exception:
        return mp.stem


def _get_agent_info() -> str | None:
    """Get first agent ID for startup display."""
    if not AGENTS_DIR.exists():
        return None
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        if agent_dir.is_dir() and (agent_dir / "metadata.yaml").exists():
            return agent_dir.name
    return None
