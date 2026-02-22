"""vest audit — audit trail commands."""

import json

import click

from vestbridge.cli.main import cli


@cli.group()
def audit() -> None:
    """Audit trail commands."""


@audit.command()
@click.option("--agent", default=None, help="Agent ID (default: first agent)")
def verify(agent: str | None) -> None:
    """Verify audit log hash chain integrity."""
    from vestbridge.audit.verifier import AuditVerifier
    from vestbridge.identity.agent import get_agent_audit_path, get_or_create_default_agent

    agent_id = agent or get_or_create_default_agent().agent_id
    audit_path = get_agent_audit_path(agent_id)

    if not audit_path.exists():
        click.echo(f"No audit log found for agent {agent_id}")
        return

    verifier = AuditVerifier()
    result = verifier.verify(audit_path)

    if result.valid:
        click.echo(f"Audit log verified: {result.entries_checked} entries, chain intact.")
    else:
        click.echo(f"VERIFICATION FAILED at entry {result.entries_checked}")
        click.echo(f"Error: {result.first_error}")
        raise SystemExit(1)


@audit.command()
@click.option("--agent", default=None, help="Agent ID (default: first agent)")
@click.option("--last", "n", default=20, type=int, help="Number of entries to show")
def show(agent: str | None, n: int) -> None:
    """Print recent audit entries."""
    from vestbridge.audit.logger import AuditLogger
    from vestbridge.identity.agent import get_agent_audit_path, get_or_create_default_agent

    agent_id = agent or get_or_create_default_agent().agent_id
    audit_path = get_agent_audit_path(agent_id)

    if not audit_path.exists():
        click.echo(f"No audit log found for agent {agent_id}")
        return

    logger = AuditLogger(audit_path)
    entries = logger.read_entries(last_n=n)

    for entry in entries:
        check_str = ""
        if entry.mandate_check:
            check_str = f" [{entry.mandate_check}]"
        click.echo(f"  {entry.timestamp.isoformat()[:19]}  {entry.action:<15}{check_str}")
        if entry.mandate_reason:
            click.echo(f"    reason: {entry.mandate_reason}")


@audit.command()
@click.option("--agent", default=None, help="Agent ID (default: first agent)")
@click.option("--format", "fmt", default="json", type=click.Choice(["json", "csv"]))
@click.option("--output", "output_path", default=None, help="Output file path")
def export(agent: str | None, fmt: str, output_path: str | None) -> None:
    """Export audit log to JSON or CSV."""
    import csv
    import io

    from vestbridge.audit.logger import AuditLogger
    from vestbridge.identity.agent import get_agent_audit_path, get_or_create_default_agent

    agent_id = agent or get_or_create_default_agent().agent_id
    audit_path = get_agent_audit_path(agent_id)

    if not audit_path.exists():
        click.echo(f"No audit log found for agent {agent_id}")
        return

    logger = AuditLogger(audit_path)
    entries = logger.read_entries()

    if fmt == "json":
        data = [e.model_dump(mode="json") for e in entries]
        content = json.dumps(data, indent=2, default=str)
    else:
        output = io.StringIO()
        if entries:
            fields = list(entries[0].model_dump().keys())
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            for entry in entries:
                row = entry.model_dump(mode="json")
                row["params"] = json.dumps(row["params"])
                if row["result"]:
                    row["result"] = json.dumps(row["result"])
                writer.writerow(row)
        content = output.getvalue()

    if output_path:
        with open(output_path, "w") as f:
            f.write(content)
        click.echo(f"Exported {len(entries)} entries to {output_path}")
    else:
        click.echo(content)
