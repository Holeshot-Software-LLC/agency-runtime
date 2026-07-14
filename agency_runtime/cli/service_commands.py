"""HTTP, MCP, hook, and dashboard service commands."""

from __future__ import annotations

import argparse
import time

from agency_runtime.core.configuration import resolve_config_path
from agency_runtime.core.store.sqlite import Store

from ._common import print_json as _print_json


def cmd_serve(args: argparse.Namespace) -> int:
    from agency_runtime.server.http import serve

    serve()
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from agency_runtime.server.mcp import run_stdio

    store = Store(args.db) if args.db else None
    return run_stdio(store=store)


def cmd_hook(args: argparse.Namespace) -> int:
    from agency_runtime.adapters.hooks import run_hook_stdio

    store = Store(args.db) if args.db else None
    return run_hook_stdio(args.host, store=store)


def cmd_dashboard(args: argparse.Namespace) -> int:
    from agency_runtime.server.dashboard import run_dashboard

    run_dashboard(
        port=args.port,
        db_path=args.db,
        open_browser=not args.no_open,
        service_mode=bool(getattr(args, "service_mode", False)),
        config_path=getattr(args, "config", None),
    )
    return 0


def _wait_dashboard_ready(timeout_seconds: float = 8.0) -> bool:
    from agency_runtime.core.dashboard_runtime import dashboard_service_reachable

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if dashboard_service_reachable(timeout=0.5):
            return True
        time.sleep(0.1)
    return False


def cmd_dashboard_service(args: argparse.Namespace) -> int:
    from agency_runtime.core.dashboard_runtime import (
        dashboard_service_reachable,
        open_dashboard_service,
    )
    from agency_runtime.core.dashboard_service import (
        inspect_dashboard_service,
        install_dashboard_service,
        plan_dashboard_service,
        restart_dashboard_service,
        start_dashboard_service,
        stop_dashboard_service,
        uninstall_dashboard_service,
    )

    action = args.dashboard_service_action
    common = {"config_path": resolve_config_path()}
    if action == "open":
        result = open_dashboard_service(open_browser=not args.no_open)
    elif action == "status":
        result = inspect_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    elif action == "install" and args.dry_run:
        result = plan_dashboard_service(**common)
    elif action == "install":
        result = install_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "start":
        result = start_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "stop":
        result = stop_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    elif action == "restart":
        result = restart_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "uninstall":
        result = uninstall_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    else:  # parser choices make this defensive only
        raise ValueError(f"unknown dashboard service action: {action}")

    if args.json:
        _print_json(result)
    elif result.get("ok"):
        status = result.get("status") or result.get("action") or action
        print(f"✅ Dashboard service {status}")
        if action == "open":
            print(f"   {result.get('url')}")
        elif action in {"install", "start", "restart"}:
            print("   Open it with: agency dashboard service open")
        if result.get("reachable") is False:
            print("   Warning: registration exists, but the dashboard is not reachable.")
    else:
        print(f"❌ Dashboard service {action}: {result.get('error', 'operation failed')}")
    return int(result.get("exit_code", 0 if result.get("ok") else 1))
