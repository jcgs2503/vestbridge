"""CLI entrypoint for VestBridge."""

import vestbridge.cli.agent_cmd  # noqa: F401
import vestbridge.cli.audit_cmd  # noqa: F401
import vestbridge.cli.init  # noqa: F401
import vestbridge.cli.mandate_cmd  # noqa: F401
import vestbridge.cli.serve  # noqa: F401
from vestbridge.cli.main import cli


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
