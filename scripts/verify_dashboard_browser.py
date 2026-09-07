"""Run optional packaged-dashboard browser QA in a private, offline fixture.

Install pinned Playwright/axe development tools in a disposable npm prefix and
pass it with --tools. Select the installed wheel through PYTHONPATH and require
its exact --package-root. This command never installs or activates a host.
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", type=Path, required=True, help="Disposable npm prefix")
    parser.add_argument("--package-root", type=Path, required=True, help="Installed wheel target")
    parser.add_argument("--output", type=Path, required=True, help="New evidence directory")
    parser.add_argument("--browser", help="Optional Chromium executable; default is Playwright's")
    args = parser.parse_args()
    os.umask(0o077)
    for name in tuple(os.environ):
        if name.startswith("AGENCY_") or name in {
            "OLLAMA_BASE_URL",
            "LITELLM_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
        }:
            os.environ.pop(name)

    with tempfile.TemporaryDirectory(prefix="agency-dashboard-qa-") as directory:
        fixture = Path(directory)
        os.environ["AGENCY_CONFIG_PATH"] = str(fixture / "agency.yaml")
        os.environ["AGENCY_DB_PATH"] = str(fixture / "dashboard.db")
        os.environ["AGENCY_JUDGE_TIMEOUT"] = "0.05"

        import agency_runtime
        from agency_runtime.core.roster.bundled import bundled_roster
        from agency_runtime.core.store.sqlite import Store
        from agency_runtime.server.dashboard import DashboardHTTPServer

        package = Path(agency_runtime.__file__).resolve().parent
        if package.parent != args.package_root.resolve():
            parser.error("PYTHONPATH did not select the required installed package root")
        args.output.mkdir(parents=True, exist_ok=False)
        store = Store()
        store.activate_agents_if_missing(list(bundled_roster())[:5])
        token = secrets.token_urlsafe(32)
        server = DashboardHTTPServer(
            store,
            auth_token=token,
            port=0,
            host_inspector=lambda: [],
            runtime_control_home=fixture,
        )

        # The server can accept browser traffic but cannot contact any provider,
        # local model, update endpoint or native host during this fixture.
        def deny_outbound(event: str, _arguments: object) -> None:
            if event == "socket.connect":
                raise OSError("Outbound requests disabled in browser QA fixture")

        sys.addaudithook(deny_outbound)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = subprocess.run(
                [
                    "node",
                    str(Path(__file__).with_suffix(".mjs")),
                    str(args.tools.resolve()),
                    str(args.output.resolve()),
                    args.browser or "",
                    str(package),
                ],
                env={
                    **os.environ,
                    "QA_URL": f"http://127.0.0.1:{server.server_address[1]}",
                    "QA_TOKEN": token,
                },
                check=False,
                timeout=180,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
