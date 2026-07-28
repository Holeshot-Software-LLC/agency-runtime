"""Version inspection and non-mutating attended-upgrade planning commands."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from typing import Any

from agency_runtime.core.update_service import (
    attended_upgrade_plan,
    cached_update_status,
    check_for_update,
    installed_version_snapshot,
)


def _print_json(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, allow_nan=False, indent=2, sort_keys=True))


def _target_kwargs(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "channel": getattr(args, "channel", None),
        "version": getattr(args, "target_version", None),
        "ref": getattr(args, "target_ref", None),
    }


def _status(args: argparse.Namespace) -> dict[str, Any]:
    kwargs = _target_kwargs(args)
    if bool(getattr(args, "cached", False)):
        return cached_update_status(**kwargs)
    return check_for_update(
        **kwargs,
        refresh=bool(getattr(args, "refresh", False)),
        timeout=float(getattr(args, "timeout", None) or 5.0),
    )


def _human_identity(identity: Mapping[str, Any]) -> None:
    print(f"Agency Runtime {identity['package_version']}")
    print(f"Build: {identity['build_identity']}")
    print(f"Install: {identity['install_kind']}")
    revision = identity.get("source_revision")
    if revision:
        print(f"Source commit: {revision}")
    else:
        print("Source commit: unavailable")


def _human_status(status: Mapping[str, Any]) -> None:
    _human_identity(status["installed"])
    selector = status["selector"]
    print(f"Target: {selector['value']} ({selector['kind']})")
    target = status.get("target")
    if isinstance(target, Mapping):
        label = target.get("label") or target.get("ref")
        print(f"Resolved: {label} @ {target['commit_sha']}")
        print(f"Source: {target['url']}")
    print(f"Status: {status['status']}")
    if status.get("error"):
        print(f"Check: {status['error']}")


def cmd_version(args: argparse.Namespace) -> int:
    wants_check = bool(getattr(args, "check", False)) or any(
        getattr(args, name, None)
        for name in (
            "channel",
            "target_version",
            "target_ref",
            "refresh",
            "cached",
            "timeout",
        )
    )
    if wants_check:
        status = _status(args)
        if bool(getattr(args, "json", False)):
            _print_json(status)
        else:
            _human_status(status)
        return 0 if status.get("checked") and not status.get("error") else 1
    identity = installed_version_snapshot()
    if bool(getattr(args, "json", False)):
        _print_json({"schema_version": "agency.version.v1", **identity})
    else:
        _human_identity(identity)
    return 0


def cmd_upgrade(args: argparse.Namespace) -> int:
    check_only = getattr(args, "upgrade_action", "plan") == "check"
    status = _status(args)
    payload: dict[str, Any] = dict(status)
    if not check_only:
        payload["plan"] = attended_upgrade_plan(status)
    if bool(getattr(args, "json", False)):
        _print_json(payload)
    else:
        _human_status(payload)
        if not check_only:
            plan = payload["plan"]
            print()
            print("Attended upgrade plan")
            print(plan["reason"])
            for index, command in enumerate(plan.get("commands", ()), start=1):
                print(f"  {index}. {command['display']}")
            if plan.get("commands"):
                print("No command was executed by Agency Runtime.")
    return 0 if status.get("checked") and not status.get("error") else 1


__all__ = ["cmd_upgrade", "cmd_version"]
