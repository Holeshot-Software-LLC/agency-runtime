"""Minimal persistent dashboard-service entry point.

The long-lived worker must not import the complete interactive CLI command
graph before it can publish its readiness descriptor.  This module validates
the service's fixed argument shape first and imports only the dashboard server.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the loopback dashboard from one explicit durable config path."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] != "--config" or not arguments[1].strip():
        print(
            "usage: agency_runtime.server.dashboard_service --config <path>",
            file=sys.stderr,
        )
        return 2

    from agency_runtime.server.dashboard import run_dashboard

    run_dashboard(
        open_browser=False,
        service_mode=True,
        config_path=arguments[1],
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through the private launcher
    raise SystemExit(main())
