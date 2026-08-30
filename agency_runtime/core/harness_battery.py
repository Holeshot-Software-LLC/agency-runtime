"""Change-triggered harness canary battery (AR-337).

Host CLIs auto-update on their own cadence and nothing on the host is
pinned, so contract drift lands silently. The battery keeps one proven
version fingerprint per harness and, when the observed version differs,
re-proves that harness with its strongest unattended check: the proven
canary mode where one exists (claude, codex current-profile), the
staffing-complete ordinary check where none does (hermes, openclaw), and a
content-free posture scan of the harness install tree. Receipts are
retained privately and doctor surfaces the last outcome per harness.

The battery never mutates host-owned trees and never bypasses attended
trust: a codex canary refused at the trust boundary is reported as the
distinct loud outcome ``attended_trust_required`` (owner interview,
2026-08-30).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.private_paths import ensure_private_directory

BATTERY_SCHEMA = "agency.harness-battery.v1"
BATTERY_HOSTS = ("claude", "codex", "hermes", "openclaw")
BATTERY_OUTCOMES = frozenset({"passed", "failed", "attended_trust_required"})
_VERSION_TIMEOUT_SECONDS = 30.0
_TURN_TIMEOUT_SECONDS = 420.0
_MAX_POSTURE_ENTRIES = 4000
_MAX_VERSION_CHARS = 200
_ORDINARY_TASK = (
    "Review the error handling in this project's configuration loader and "
    "report the single highest risk you can justify from the code."
)
_CANARY_CONFIRMATIONS = {
    "claude": "RUN LIVE claude CANARY",
    "codex": "RUN LIVE codex CURRENT-PROFILE CANARY",
}

_VERSION_COMMANDS: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "--version"),
    "codex": ("codex", "--version"),
    "hermes": ("hermes", "--version"),
    "openclaw": ("openclaw", "--version"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_fingerprint_path() -> Path:
    return Path("~/.agency-runtime/harness-battery.json").expanduser()


def default_receipt_root() -> Path:
    return Path("~/.agency-runtime/evidence/harness-battery").expanduser()


def _bounded_process(
    command: tuple[str, ...],
    *,
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def observe_harness_version(
    host: str,
    *,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = _bounded_process,
) -> str:
    """Return the first observed version line for one harness, or ""."""

    command = _VERSION_COMMANDS.get(host)
    if command is None or not resolver(command[0]):
        return ""
    try:
        completed = runner(command, timeout=_VERSION_TIMEOUT_SECONDS)
    except Exception:
        return ""
    if getattr(completed, "returncode", 1) != 0:
        return ""
    first_line = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    observed = first_line[0].strip() if first_line else ""
    return observed[:_MAX_VERSION_CHARS]


def read_fingerprints(path: Path | None = None) -> dict[str, Any]:
    """Read the fingerprint document; absent or invalid reads as empty."""

    target = default_fingerprint_path() if path is None else path
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"schema": BATTERY_SCHEMA, "harnesses": {}}
    harnesses = raw.get("harnesses") if isinstance(raw, dict) else None
    if raw.get("schema") != BATTERY_SCHEMA or not isinstance(harnesses, dict):
        return {"schema": BATTERY_SCHEMA, "harnesses": {}}
    return {"schema": BATTERY_SCHEMA, "harnesses": dict(harnesses)}


def _write_fingerprints(document: Mapping[str, Any], path: Path) -> None:
    ensure_private_directory(path.parent)
    serialized = json.dumps(document, indent=1, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(descriptor, serialized.encode("utf-8"))
    finally:
        os.close(descriptor)


def changed_harnesses(
    observed: Mapping[str, str],
    fingerprints: Mapping[str, Any],
) -> tuple[str, ...]:
    """Harnesses whose observed version differs from the proven fingerprint.

    An unobservable harness (empty version) is never battery-triggered: the
    battery proves change, and absence is a doctor concern, not a drill.
    """

    harnesses = fingerprints.get("harnesses")
    known = harnesses if isinstance(harnesses, Mapping) else {}
    changed: list[str] = []
    for host in BATTERY_HOSTS:
        version = observed.get(host, "")
        if not version:
            continue
        entry = known.get(host)
        proven = entry.get("proven_version") if isinstance(entry, Mapping) else ""
        if version != proven:
            changed.append(host)
    return tuple(changed)


def _posture_root(executable: Path) -> Path:
    """Resolve the bounded posture-scan root for one harness executable."""

    resolved = executable.resolve()
    for parent in resolved.parents:
        if parent.name == "node_modules":
            relative = resolved.relative_to(parent)
            top = relative.parts[0]
            if top.startswith("@") and len(relative.parts) > 1:
                return parent / top / relative.parts[1]
            return parent / top
    return resolved.parent


def posture_regressions(
    host: str,
    *,
    resolver: Callable[[str], str | None] = shutil.which,
) -> dict[str, int]:
    """Count group- or other-writable entries in one harness install tree.

    Content-free by construction: only bounded counts leave this function.
    The battery reports; it never remediates host-owned trees unattended.
    """

    counts = {"scanned": 0, "group_writable": 0, "other_writable": 0}
    command = _VERSION_COMMANDS.get(host)
    located = resolver(command[0]) if command else None
    if not located:
        return counts
    root = _posture_root(Path(located))
    entries = [root, *root.rglob("*")] if root.is_dir() else [root]
    for entry in entries:
        if counts["scanned"] >= _MAX_POSTURE_ENTRIES:
            break
        try:
            mode = entry.lstat().st_mode
        except OSError:
            continue
        counts["scanned"] += 1
        if mode & 0o020:
            counts["group_writable"] += 1
        if mode & 0o002:
            counts["other_writable"] += 1
    return counts


def _canary_outcome(report: Mapping[str, Any]) -> tuple[str, str]:
    """Map one canary report to a battery outcome and content-free reason."""

    if report.get("canary_passed") is True:
        return "passed", ""
    invocation = report.get("invocation")
    reason = str(invocation.get("failure_reason") or "") if isinstance(invocation, Mapping) else ""
    if reason == "codex_hook_trust_not_ready":
        return "attended_trust_required", reason
    return "failed", reason or "canary_failed"


def _run_canary_battery(
    host: str,
    *,
    canary_runner: Callable[..., Mapping[str, Any]],
    config_path: str | None,
) -> tuple[str, dict[str, Any]]:
    keywords: dict[str, Any] = {
        "execute": True,
        "confirm": _CANARY_CONFIRMATIONS[host],
        "mode": "agency",
        "timeout": _TURN_TIMEOUT_SECONDS,
        "config_path": config_path,
    }
    if host == "codex":
        keywords["profile_scope"] = "current-profile"
        keywords["require_existing_store"] = True
    report = canary_runner(host, **keywords)
    outcome, reason = _canary_outcome(report)
    return outcome, {
        "mode": "canary",
        "outcome": outcome,
        "reason": reason,
        "canary_passed": report.get("canary_passed") is True,
        "attestation_persisted": report.get("attestation_persisted") is True,
    }


_ORDINARY_COMMANDS: dict[str, tuple[str, ...]] = {
    "hermes": ("hermes", "-z", _ORDINARY_TASK),
    "openclaw": ("openclaw", "agent", "-m", _ORDINARY_TASK, "--json"),
}


def _store_activity_index(store: Any) -> dict[str, set[str]]:
    activity = store.recent_runtime_activity(limit=200)
    return {
        name: {str(row.get("id") or f"{name}-{index}") for index, row in enumerate(rows)}
        for name, rows in activity.items()
    }


def _run_ordinary_battery(
    host: str,
    *,
    store: Any,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any],
) -> tuple[str, dict[str, Any]]:
    """Staffing-complete ordinary check for hosts without a canary mode."""

    command = _ORDINARY_COMMANDS[host]
    if not resolver(command[0]):
        return "failed", {
            "mode": "ordinary",
            "outcome": "failed",
            "reason": "harness_executable_unavailable",
        }
    before = _store_activity_index(store)
    try:
        completed = runner(command, timeout=_TURN_TIMEOUT_SECONDS)
        timed_out = False
        exit_code = getattr(completed, "returncode", 1)
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_code = None
    time.sleep(3)
    after = store.recent_runtime_activity(limit=200)
    fresh: dict[str, int] = {}
    zero_preflight = True
    for name, rows in after.items():
        prior = before.get(name, set())
        new_rows = [
            row
            for index, row in enumerate(rows)
            if str(row.get("id") or f"{name}-{index}") not in prior
        ]
        if new_rows:
            fresh[name] = len(new_rows)
        if name == "preflight_failures" and new_rows:
            zero_preflight = False
    staffed = (
        not timed_out
        and exit_code == 0
        and fresh.get("runs", 0) >= 1
        and fresh.get("routing", 0) >= 1
        and fresh.get("specialists", 0) >= 1
        and zero_preflight
    )
    outcome = "passed" if staffed else "failed"
    return outcome, {
        "mode": "ordinary",
        "outcome": outcome,
        "reason": "" if staffed else "ordinary_turn_not_staffing_complete",
        "timed_out": timed_out,
        "exit_code": exit_code,
        "new_row_counts": fresh,
    }


def _write_receipt(
    root: Path,
    host: str,
    payload: Mapping[str, Any],
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = root / f"{stamp}-{host}"
    ensure_private_directory(directory)
    target = directory / "receipt.json"
    serialized = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(descriptor, serialized.encode("utf-8"))
    finally:
        os.close(descriptor)
    return str(target)


def run_battery(
    *,
    hosts: tuple[str, ...] | None = None,
    force: bool = False,
    config_path: str | None = None,
    fingerprint_path: Path | None = None,
    receipt_root: Path | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = _bounded_process,
    canary_runner: Callable[..., Mapping[str, Any]] | None = None,
    store_factory: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Observe versions, run the battery for changed harnesses, seal receipts."""

    if canary_runner is None:
        from agency_runtime.core.canary import run_canary as canary_runner
    selected = tuple(hosts) if hosts else BATTERY_HOSTS
    for host in selected:
        if host not in BATTERY_HOSTS:
            raise ValueError(f"unsupported battery harness: {host}")
    fingerprint_file = fingerprint_path or default_fingerprint_path()
    receipts = receipt_root or default_receipt_root()
    document = read_fingerprints(fingerprint_file)
    observed = {
        host: observe_harness_version(host, resolver=resolver, runner=runner) for host in selected
    }
    due = tuple(
        host
        for host in selected
        if observed.get(host) and (force or host in changed_harnesses(observed, document))
    )
    results: dict[str, Any] = {}
    for host in due:
        posture = posture_regressions(host, resolver=resolver)
        if host in _CANARY_CONFIRMATIONS:
            outcome, detail = _run_canary_battery(
                host,
                canary_runner=canary_runner,
                config_path=config_path,
            )
        else:
            if store_factory is None:
                from agency_runtime.core.config import load_config
                from agency_runtime.core.store.sqlite import Store

                database = Path(load_config(config_path).store.db_path).expanduser()

                def _open_store(path: Path = database) -> Any:
                    return Store(path)

                store_factory = _open_store
            outcome, detail = _run_ordinary_battery(
                host,
                store=store_factory(),
                resolver=resolver,
                runner=runner,
            )
        detail["posture"] = posture
        detail["observed_version"] = observed[host]
        detail["ran_at"] = _now()
        receipt = _write_receipt(receipts, host, detail)
        entry = {
            "last_outcome": outcome,
            "last_run_at": detail["ran_at"],
            "last_receipt": receipt,
            "observed_version": observed[host],
            "posture_group_writable": posture["group_writable"],
        }
        previous = document["harnesses"].get(host)
        proven = previous.get("proven_version") if isinstance(previous, Mapping) else ""
        entry["proven_version"] = observed[host] if outcome == "passed" else proven or ""
        if outcome == "passed":
            entry["proven_at"] = detail["ran_at"]
        elif isinstance(previous, Mapping) and previous.get("proven_at"):
            entry["proven_at"] = previous["proven_at"]
        document["harnesses"][host] = entry
        results[host] = detail
    if due:
        _write_fingerprints(document, fingerprint_file)
    failed = [host for host, detail in results.items() if detail["outcome"] != "passed"]
    return {
        "schema": BATTERY_SCHEMA,
        "observed": observed,
        "ran": list(due),
        "results": results,
        "failed": failed,
        "ok": not failed,
    }


def record_baseline(
    *,
    hosts: tuple[str, ...] | None = None,
    fingerprint_path: Path | None = None,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = _bounded_process,
) -> dict[str, Any]:
    """Adopt current harness versions as the proven baseline without running.

    The battery proves change; the baseline is the reference point. The
    installer records it after a verified install, and the operator can
    re-adopt explicitly after proving harnesses by other means.
    """

    selected = tuple(hosts) if hosts else BATTERY_HOSTS
    for host in selected:
        if host not in BATTERY_HOSTS:
            raise ValueError(f"unsupported battery harness: {host}")
    fingerprint_file = fingerprint_path or default_fingerprint_path()
    document = read_fingerprints(fingerprint_file)
    adopted: dict[str, str] = {}
    stamp = _now()
    for host in selected:
        version = observe_harness_version(host, resolver=resolver, runner=runner)
        if not version:
            continue
        entry = dict(document["harnesses"].get(host) or {})
        entry.update(
            {
                "proven_version": version,
                "proven_at": stamp,
                "observed_version": version,
                "last_outcome": entry.get("last_outcome") or "passed",
                "last_run_at": entry.get("last_run_at") or stamp,
            }
        )
        document["harnesses"][host] = entry
        adopted[host] = version
    if adopted:
        _write_fingerprints(document, fingerprint_file)
    return {"schema": BATTERY_SCHEMA, "baseline": adopted}


def run_battery_cli(args: Any) -> int:
    """CLI adapter for ``agency battery``."""

    if getattr(args, "install_service", False):
        from agency_runtime.core.battery_service import install_battery_service

        report = install_battery_service()
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0 if report["installed"] else 1
    if getattr(args, "uninstall_service", False):
        from agency_runtime.core.battery_service import uninstall_battery_service

        report = uninstall_battery_service()
        print(json.dumps(report, indent=1, sort_keys=True))
        return 0
    hosts = (str(args.host),) if getattr(args, "host", None) else None
    if getattr(args, "baseline", False):
        report = record_baseline(hosts=hosts)
        if getattr(args, "json", False):
            print(json.dumps(report, indent=1, sort_keys=True))
        else:
            for host, version in sorted(report["baseline"].items()):
                print(f"{host}: baseline {version}")
        return 0
    report = run_battery(
        hosts=hosts,
        force=bool(getattr(args, "force", False)),
        config_path=getattr(args, "config", None),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=1, sort_keys=True))
    elif not report["ran"]:
        print("harness battery: no harness version change detected")
    else:
        for host in report["ran"]:
            detail = report["results"][host]
            print(f"{host}: {detail['outcome']} ({detail['observed_version']})")
    return 0 if report["ok"] else 1
