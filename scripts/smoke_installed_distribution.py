"""Exercise critical surfaces from an installed distribution, outside the checkout."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import urllib.request
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

from agency_runtime import __version__
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    OllamaConfig,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.host_capabilities import native_adapter_capability_receipt
from agency_runtime.core.private_paths import (
    ensure_private_directory,
    private_temporary_directory,
)
from agency_runtime.core.roster.bundled import bundled_manifest, bundled_roster
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.selector.cache import clear_cache
from agency_runtime.core.selector.pipeline import route
from agency_runtime.core.selector.stickiness import clear_session_routing
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server.dashboard import DashboardHTTPServer

_MAX_PROTOCOL_OUTPUT = 1024 * 1024
_DASHBOARD_ASSETS = (
    "app.css",
    "app.js",
    "charts.js",
    "dashboard-actions.js",
    "dashboard-config.js",
    "dashboard-core.js",
    "dashboard-live.js",
    "dashboard-render.js",
    "index.html",
    "package.json",
)


def _mcp_transcript(python: str, root: Path) -> dict[str, object]:
    messages = (
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "distribution-smoke", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "agency.status", "arguments": {}},
        },
    )
    transcript = "\n".join(json.dumps(message) for message in messages) + "\n"
    environment = os.environ.copy()
    environment["AGENCY_DB_PATH"] = str(root / "mcp.db")
    completed = subprocess.run(
        [python, "-I", "-m", "agency_runtime.server.mcp", "--stdio"],
        input=transcript,
        capture_output=True,
        text=True,
        cwd=root,
        env=environment,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError(
            f"packaged MCP failed with exit {completed.returncode}: {completed.stderr[:500]}"
        )
    if len(completed.stdout.encode("utf-8")) > _MAX_PROTOCOL_OUTPUT:
        raise RuntimeError("packaged MCP output exceeded the smoke limit")
    responses = [
        safe_load_bounded_json(line, maximum_bytes=_MAX_PROTOCOL_OUTPUT)
        for line in completed.stdout.splitlines()
    ]
    by_id = {
        response.get("id"): response
        for response in responses
        if isinstance(response, dict) and response.get("id") is not None
    }
    tools = by_id.get(2, {}).get("result", {}).get("tools", [])
    tool_names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    status = by_id.get(3, {}).get("result", {})
    if "agency.status" not in tool_names or status.get("isError") is not False:
        raise RuntimeError("packaged MCP did not expose and execute agency.status")
    return {"tool_count": len(tool_names), "status_call": "passed"}


def _dashboard_round_trip(root: Path) -> dict[str, object]:
    token = "distribution-smoke-dashboard-token"
    server = DashboardHTTPServer(
        Store(root / "dashboard.db"),
        auth_token=token,
        port=0,
        host_inspector=lambda: [],
    )
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    port = int(server.server_address[1])
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/health",
        headers={"Authorization": f"Bearer {token}"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=5) as response:
            payload = safe_load_bounded_json(response.read(4097), maximum_bytes=4096)
            if response.status != 200 or payload != {"status": "ok"}:
                raise RuntimeError("packaged dashboard health response is invalid")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    if thread.is_alive():
        raise RuntimeError("packaged dashboard did not stop cleanly")
    return {"bind": "127.0.0.1", "health": "passed"}


def _roster_integrity() -> dict[str, int]:
    manifest = bundled_manifest()
    roster = bundled_roster()
    counts = manifest["counts"]
    if len(roster) != counts["approved"]:
        raise RuntimeError("installed bundled roster count does not match its manifest")
    if counts["total"] != counts["approved"] + counts["quarantined"] + counts["retired"]:
        raise RuntimeError("installed bundled roster status counts are incomplete")
    slugs = {str(agent["slug"]) for agent in roster}
    if not {"agents-orchestrator", "chief-of-staff"}.issubset(slugs):
        raise RuntimeError("installed bundled roster is missing resident managers")
    if any(
        not str(agent.get("prompt_body") or "").strip()
        or not str(agent.get("version") or "").startswith("sha256:")
        for agent in roster
    ):
        raise RuntimeError("installed bundled roster contains an invalid approved prompt")
    return {key: int(value) for key, value in counts.items()}


def _selection_safety() -> dict[str, object]:
    manifest = bundled_manifest()
    cards = [
        selector_roster_projection(
            {
                **entry,
                "agent_slug": entry["slug"],
                "name": entry["display_name"],
            }
        )
        for entry in manifest["agents"]
        if entry["audit_status"] == "approved"
    ]
    offline = AgencyConfig(
        providers=(),
        judge=JudgeConfig(model="", base_url="", confidence_bypass_threshold=999.0),
        ollama=OllamaConfig(enabled=False, model=""),
    )
    cases = (
        (
            "agency-runtime-dashboard",
            "The Agency response header exposes unreadable reason codes and effect codes. "
            "Explain how to test agent selection live and how to open the dashboard.",
            ("multi-agent-systems-architect",),
            ("technical-writer",),
        ),
        ("ambiguous-help", "Please help me with this.", (), ()),
    )
    observed: dict[str, list[str]] = {}
    forbidden = {"clinical-evidence-agent", "geographer", "language-translator"}
    platform_name = "windows" if os.name == "nt" else "linux"
    for case_id, message, required, acceptable in cases:
        clear_cache()
        clear_session_routing()
        session_id = f"installed-selection-{case_id}"
        trace_id = f"installed-selection-trace-{case_id}"
        capability = native_adapter_capability_receipt(
            "codex",
            platform=platform_name,
            session_id=session_id,
            trace_id=trace_id,
        )
        decision = route(
            session_id,
            message,
            cards,
            config=offline,
            host="codex",
            platform=platform_name,
            capability_receipt=capability,
            capability_session_id=session_id,
            capability_trace_id=trace_id,
            trace_id=trace_id,
        )
        selected = tuple(str(item) for item in decision.get("semantic_ids", []))
        selected_set = set(selected)
        allowed = set(required) | set(acceptable)
        if (
            not set(required).issubset(selected_set)
            or not selected_set.issubset(allowed)
            or forbidden.intersection(selected_set)
        ):
            raise RuntimeError(
                "installed selection safety failed for "
                f"{case_id}: selected={selected!r}, required={required!r}, "
                f"acceptable={acceptable!r}"
            )
        observed[case_id] = list(selected)
    return {
        "status": "passed",
        "cases": observed,
        "forbidden_specialists": sorted(forbidden),
    }


def run(*, artifact_set: str | None = None) -> dict[str, object]:
    installed_version = version("agency-runtime")
    if installed_version != __version__:
        raise RuntimeError("package metadata and runtime versions disagree")
    dashboard = files("agency_runtime.dashboard")
    missing = [name for name in _DASHBOARD_ASSETS if not dashboard.joinpath(name).is_file()]
    if missing:
        raise RuntimeError(f"installed distribution is missing dashboard assets: {missing}")
    roster = _roster_integrity()
    selection = _selection_safety()
    with private_temporary_directory(prefix="distribution-smoke") as root:
        isolated_home = ensure_private_directory(root / "home")
        os.environ.update(
            {
                "AGENCY_CONFIG_PATH": str(root / "agency.yaml"),
                "AGENCY_DB_PATH": str(root / "agency.db"),
                "HOME": str(isolated_home),
                "USERPROFILE": str(isolated_home),
            }
        )
        reset_config_cache()
        try:
            config = load_config(reload=True)
            if config.server.host not in {"127.0.0.1", "::1", "localhost"}:
                raise RuntimeError("packaged default server configuration is not loopback-only")
            mcp = _mcp_transcript(sys.executable, root)
            dashboard_result = _dashboard_round_trip(root)
        finally:
            reset_config_cache()
    return {
        "version": installed_version,
        "assets": len(_DASHBOARD_ASSETS),
        "config": "passed",
        "roster": roster,
        "selection": selection,
        "artifact_set": artifact_set,
        "mcp": mcp,
        "dashboard": dashboard_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-version")
    parser.add_argument("--artifact-set", choices=("portable", "windows-x64"))
    args = parser.parse_args()
    result = run(artifact_set=args.artifact_set)
    if args.expected_version and result["version"] != args.expected_version:
        raise RuntimeError("installed version does not match the expected release version")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
