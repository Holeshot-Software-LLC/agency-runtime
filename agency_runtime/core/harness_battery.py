"""Change-triggered harness canary battery (AR-337).

Host CLIs auto-update on their own cadence and nothing on the host is
pinned, so contract drift lands silently. The battery keeps one proven
version fingerprint per harness and, when the observed version differs,
re-proves that harness with its strongest unattended check: the proven
canary mode where one exists (claude, codex current-profile), the
staffing-complete ordinary check where none does (hermes, openclaw), and a
content-free posture scan of the harness install tree. Receipts are
retained privately and doctor surfaces the last outcome per harness.

Two refinements keep the verdict honest on a busy box:

* The ordinary check judges only the battery turn's own session. Its
  before/after store delta is split into own-session rows (joined through
  the new ``runs`` rows for the battery's host) and foreign-session
  activity, so another session's preflight failure in the same window is
  reported, never absorbed (AR-352).
* Every probe runs ``k`` trials and is graded. Canary probes prove wiring
  trust, hook activation, and the finalization round-trip, so they grade
  pass^k (every trial must pass); ordinary probes overlap the intermittent
  staffing window (AR-353) and grade pass@k (any passing trial proves the
  harness). Every trial is persisted so a flap is data (AR-360).

The battery never mutates host-owned trees and never bypasses attended
trust: a codex canary refused at the trust boundary is reported as the
distinct loud outcome ``attended_trust_required`` (owner interview,
2026-08-30), and that outcome short-circuits the remaining trials because
retrying an attended step cannot change its answer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core.deployed_fix_witness import WITNESS_FAILURE_STATUSES, attest_host
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.process_argv import prepare_process_argv

BATTERY_SCHEMA = "agency.harness-battery.v1"
BATTERY_HOSTS = ("claude", "codex", "hermes", "openclaw")
BATTERY_OUTCOMES = frozenset({"passed", "failed", "attended_trust_required"})
# AR-360 grading modes. The data tokens are plain ASCII identifiers;
# ``pass_all_k`` is documented as pass^k (every trial must pass) and
# ``pass_any_k`` as pass@k (any passing trial proves the harness).
GRADING_PASS_ALL_K = "pass_all_k"
GRADING_PASS_ANY_K = "pass_any_k"
BATTERY_GRADING_MODES = frozenset({GRADING_PASS_ALL_K, GRADING_PASS_ANY_K})
BATTERY_DEFAULT_TRIALS = 2
BATTERY_MAX_TRIALS = 5
_GRADING_LABEL_PREFIXES = {GRADING_PASS_ALL_K: "pass^", GRADING_PASS_ANY_K: "pass@"}
_VERSION_TIMEOUT_SECONDS = 30.0
_TURN_TIMEOUT_SECONDS = 420.0
_MAX_POSTURE_ENTRIES = 4000
_MAX_VERSION_CHARS = 200
# ``recent_runtime_activity`` clamps to 200 rows per collection; the battery
# asks for the whole window so a busy box cannot push its own rows out.
_ACTIVITY_LIMIT = 200
_MAX_OWN_SESSIONS = 16
_MAX_SESSION_ID_CHARS = 128
_KNOWN_ROW_HOSTS = frozenset(EXECUTION_HOSTS) | frozenset(BATTERY_HOSTS)
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


def _prepare_version_argv(
    command: tuple[str, ...],
    resolver: Callable[[str], str | None],
) -> tuple[str, ...]:
    """Freeze one version probe through the shim-aware executable trust walk.

    On Windows the harness CLIs are npm command shims (``claude.cmd``), which
    CreateProcess cannot launch directly; :func:`prepare_process_argv` resolves
    them to their native executable or ``node`` plus the allowlisted CLI
    script, exactly as the canary launch path does (AR-340).
    """

    return tuple(prepare_process_argv(command, resolver=resolver))


def observe_harness_version_detail(
    host: str,
    *,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = _bounded_process,
    preparer: Callable[..., tuple[str, ...]] | None = None,
) -> tuple[str, str]:
    """Return ``(version, skip_reason)``; exactly one side is nonempty.

    The reason is a short names-only category so an empty battery baseline
    can say which hosts were skipped and why instead of succeeding silently.
    """

    prepare = _prepare_version_argv if preparer is None else preparer
    command = _VERSION_COMMANDS.get(host)
    if command is None:
        return "", "unsupported battery harness"
    if not resolver(command[0]):
        return "", "command not discovered"
    try:
        argv = tuple(prepare(command, resolver))
    except Exception as error:
        return "", f"version command is not launchable ({type(error).__name__})"
    try:
        completed = runner(argv, timeout=_VERSION_TIMEOUT_SECONDS)
    except Exception as error:
        return "", f"version command failed ({type(error).__name__})"
    returncode = getattr(completed, "returncode", 1)
    if returncode != 0:
        return "", f"version command exited {returncode}"
    first_line = str(getattr(completed, "stdout", "") or "").strip().splitlines()
    observed = first_line[0].strip() if first_line else ""
    if not observed:
        return "", "version output was empty"
    return observed[:_MAX_VERSION_CHARS], ""


def observe_harness_version(
    host: str,
    *,
    resolver: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = _bounded_process,
    preparer: Callable[..., tuple[str, ...]] | None = None,
) -> str:
    """Return the first observed version line for one harness, or ""."""

    version, _reason = observe_harness_version_detail(
        host,
        resolver=resolver,
        runner=runner,
        preparer=preparer,
    )
    return version


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
    # `--session-key main` scopes to the configured default agent. The bare
    # form relies on a gateway-memory routing binding that a gateway restart
    # discards, after which it exits 1 with "No target session selected".
    # OpenClaw 2026.8 requires an explicit --agent owner when multiple agents
    # are configured; without it the CLI refuses the turn before any send.
    "openclaw": (
        "openclaw",
        "agent",
        "--agent",
        "openclaw",
        "--session-key",
        "main",
        "-m",
        _ORDINARY_TASK,
        "--json",
    ),
}


def _row_identity(name: str, index: int, row: Mapping[str, Any]) -> str:
    """Stable identity for one activity row; positional when it has no id."""

    return str(row.get("id") or f"{name}-{index}")


def _store_activity_index(store: Any) -> dict[str, set[str]]:
    activity = store.recent_runtime_activity(limit=_ACTIVITY_LIMIT)
    return {
        name: {_row_identity(name, index, row) for index, row in enumerate(rows)}
        for name, rows in activity.items()
    }


def _new_activity_rows(
    before: Mapping[str, set[str]],
    after: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, list[Mapping[str, Any]]]:
    """Rows present in the after snapshot that the before index never saw."""

    fresh: dict[str, list[Mapping[str, Any]]] = {}
    for name, rows in after.items():
        prior = before.get(name, set())
        new_rows = [
            row for index, row in enumerate(rows) if _row_identity(name, index, row) not in prior
        ]
        if new_rows:
            fresh[name] = new_rows
    return fresh


def _own_turn_keys(
    host: str,
    new_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[set[str], set[str]]:
    """Session and trace ids of the battery turn's own runs (AR-352).

    The harness CLI never tells the battery which session it opened, so the
    turn is identified from the new ``runs`` rows for the battery's host.
    Both keys are kept: ``finalizations`` carry only a trace id, and every
    row of the turn shares its trace even when written before the run row.
    Concurrent new sessions of the same host in the same window remain
    indistinguishable; that residue is why the ordinary probe grades pass@k.
    """

    sessions: set[str] = set()
    traces: set[str] = set()
    for row in new_rows.get("runs", ()):
        if str(row.get("host") or "") != host:
            continue
        session = str(row.get("session_id") or "")
        trace = str(row.get("trace_id") or "")
        if session:
            sessions.add(session)
        if trace:
            traces.add(trace)
    return sessions, traces


def _row_is_own(row: Mapping[str, Any], sessions: set[str], traces: set[str]) -> bool:
    session = str(row.get("session_id") or "")
    trace = str(row.get("trace_id") or "")
    return (bool(session) and session in sessions) or (bool(trace) and trace in traces)


def _foreign_host_label(value: object) -> str:
    """Bound one foreign row's host to a known token; never echo free text."""

    host = str(value or "")
    if not host:
        return "unknown"
    return host if host in _KNOWN_ROW_HOSTS else "other"


def _scope_activity_delta(
    host: str,
    new_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Split the window's new rows into the turn's own and foreign ones.

    Only bounded counts and the own session ids leave. ``own_session_row_counts``
    drives the verdict; ``foreign_session_activity`` (per collection) and
    ``foreign_session_hosts`` (per known host) are informational so an
    operator can see what the window absorbed; ``new_row_counts`` keeps its
    pre-AR-352 meaning of every new row in the window regardless of session.
    """

    sessions, traces = _own_turn_keys(host, new_rows)
    own_counts: dict[str, int] = {}
    foreign_counts: dict[str, int] = {}
    foreign_hosts: dict[str, int] = {}
    for name, rows in new_rows.items():
        for row in rows:
            if _row_is_own(row, sessions, traces):
                own_counts[name] = own_counts.get(name, 0) + 1
                continue
            foreign_counts[name] = foreign_counts.get(name, 0) + 1
            label = _foreign_host_label(row.get("host"))
            foreign_hosts[label] = foreign_hosts.get(label, 0) + 1
    return {
        "own_sessions": [
            session[:_MAX_SESSION_ID_CHARS] for session in sorted(sessions)[:_MAX_OWN_SESSIONS]
        ],
        "own_session_row_counts": own_counts,
        "foreign_session_activity": foreign_counts,
        "foreign_session_hosts": foreign_hosts,
        "new_row_counts": {name: len(rows) for name, rows in new_rows.items()},
    }


def _run_ordinary_battery(
    host: str,
    *,
    store: Any,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any],
) -> tuple[str, dict[str, Any]]:
    """Staffing-complete ordinary check for hosts without a canary mode.

    The verdict is judged on the battery turn's own session only (AR-352):
    the turn must produce its own run, routing decision, and loaded
    specialist, and none of its own preflight failures. Foreign-session rows
    in the same window are counted in the detail, never judged.
    """

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
    after = store.recent_runtime_activity(limit=_ACTIVITY_LIMIT)
    scoped = _scope_activity_delta(host, _new_activity_rows(before, after))
    own = scoped["own_session_row_counts"]
    staffed = (
        not timed_out
        and exit_code == 0
        and own.get("runs", 0) >= 1
        and own.get("routing", 0) >= 1
        and own.get("specialists", 0) >= 1
        and own.get("preflight_failures", 0) == 0
    )
    outcome = "passed" if staffed else "failed"
    return outcome, {
        "mode": "ordinary",
        "outcome": outcome,
        "reason": "" if staffed else "ordinary_turn_not_staffing_complete",
        "timed_out": timed_out,
        "exit_code": exit_code,
        **scoped,
    }


def probe_mode(host: str) -> str:
    """``canary`` for hosts with a proven canary mode, else ``ordinary``."""

    return "canary" if host in _CANARY_CONFIRMATIONS else "ordinary"


def probe_grading_mode(host: str) -> str:
    """Grading mode per probe (AR-360).

    Canary probes are safety-critical (wiring trust, hook activation, the
    finalization round-trip) and grade pass^k; ordinary probes overlap the
    known-flaky staffing window (AR-353) and grade pass@k.
    """

    return GRADING_PASS_ALL_K if probe_mode(host) == "canary" else GRADING_PASS_ANY_K


def grading_label(mode: str, trials: int) -> str:
    """Human label for one grading mode and trial count: ``pass^k`` or ``pass@k``."""

    prefix = _GRADING_LABEL_PREFIXES.get(mode, "trials:")
    return f"{prefix}{trials}"


def validated_trials(trials: int | None) -> int:
    """Bound the per-probe trial count; ``None`` selects the default.

    ``k`` stays small because every trial is a real host turn with real model
    spend; a single trial remains valid for cheap deterministic probes.
    """

    if trials is None:
        return BATTERY_DEFAULT_TRIALS
    if type(trials) is not int or not 1 <= trials <= BATTERY_MAX_TRIALS:
        raise ValueError(f"battery trials must be an integer from 1 through {BATTERY_MAX_TRIALS}")
    return trials


def grade_trials(mode: str, trials: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    """Fold per-trial outcomes into one graded outcome and names-only reason.

    ``attended_trust_required`` is never a flap: one such trial grades the
    whole series with that distinct outcome and its reason. Under pass^k any
    failed trial fails the series; under pass@k only a series without a
    passing trial does. The reason names the failing trial numbers so the
    receipt says which trial to read.
    """

    if mode not in BATTERY_GRADING_MODES:
        raise ValueError(f"unsupported battery grading mode: {mode}")
    if not trials:
        return "failed", "no_trials_run"
    for trial in trials:
        if trial.get("outcome") == "attended_trust_required":
            return "attended_trust_required", str(trial.get("reason") or "attended_trust_required")
    failed = [
        str(number) for number, trial in enumerate(trials, 1) if trial.get("outcome") != "passed"
    ]
    if mode == GRADING_PASS_ALL_K and failed:
        return "failed", "pass_all_k_trial_failed:" + ",".join(failed)
    if mode == GRADING_PASS_ANY_K and len(failed) == len(trials):
        return "failed", "pass_any_k_all_trials_failed:" + ",".join(failed)
    return "passed", ""


def _run_graded_probe(
    host: str,
    *,
    trials: int,
    probe: Callable[[], tuple[str, dict[str, Any]]],
) -> tuple[str, dict[str, Any]]:
    """Run one host's probe ``trials`` times and grade the series (AR-360).

    Every requested trial runs, because a flap is exactly the measurement
    AR-353 needs, and each trial computes its own store delta so foreign
    activity is never counted twice. Only ``attended_trust_required``
    short-circuits: retrying an attended step cannot change its answer.
    """

    grading_mode = probe_grading_mode(host)
    recorded: list[dict[str, Any]] = []
    for number in range(1, trials + 1):
        outcome, detail = probe()
        detail["trial"] = number
        detail["ran_at"] = _now()
        recorded.append(detail)
        if outcome == "attended_trust_required":
            break
    outcome, reason = grade_trials(grading_mode, recorded)
    passed = [trial["trial"] for trial in recorded if trial["outcome"] == "passed"]
    failed = [trial["trial"] for trial in recorded if trial["outcome"] != "passed"]
    return outcome, {
        "mode": probe_mode(host),
        "outcome": outcome,
        "reason": reason,
        "grading": {
            "mode": grading_mode,
            "trials_requested": trials,
            "trials_run": len(recorded),
            "passed_trials": passed,
            "failed_trials": failed,
        },
        "trials": recorded,
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


def _default_store_factory(config_path: str | None) -> Callable[[], Any]:
    from agency_runtime.core.config import load_config
    from agency_runtime.core.store.sqlite import Store

    database = Path(load_config(config_path).store.db_path).expanduser()

    def _open_store(path: Path = database) -> Any:
        return Store(path)

    return _open_store


def _host_probe(
    host: str,
    *,
    canary_runner: Callable[..., Mapping[str, Any]],
    config_path: str | None,
    store_factory: Callable[[], Any] | None,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any],
) -> Callable[[], tuple[str, dict[str, Any]]]:
    """Bind one host's single-trial probe so the grader can repeat it.

    The store is opened once per host and shared by every trial, exactly as
    the single-shot battery opened it once.
    """

    if probe_mode(host) == "canary":
        return lambda: _run_canary_battery(
            host,
            canary_runner=canary_runner,
            config_path=config_path,
        )
    store = (store_factory or _default_store_factory(config_path))()
    return lambda: _run_ordinary_battery(host, store=store, resolver=resolver, runner=runner)


def _fingerprint_entry(
    previous: Any,
    *,
    outcome: str,
    detail: Mapping[str, Any],
    observed_version: str,
    receipt: str,
) -> dict[str, Any]:
    """Fingerprint row for one host; proof advances only on a passed battery."""

    grading = detail["grading"]
    entry: dict[str, Any] = {
        "last_outcome": outcome,
        "last_run_at": detail["ran_at"],
        "last_receipt": receipt,
        "observed_version": observed_version,
        "posture_group_writable": detail["posture"]["group_writable"],
        "last_grading_mode": grading["mode"],
        "last_trials": {
            "requested": grading["trials_requested"],
            "run": grading["trials_run"],
            "passed": len(grading["passed_trials"]),
        },
    }
    proven = previous.get("proven_version") if isinstance(previous, Mapping) else ""
    entry["proven_version"] = observed_version if outcome == "passed" else proven or ""
    if outcome == "passed":
        entry["proven_at"] = detail["ran_at"]
    elif isinstance(previous, Mapping) and previous.get("proven_at"):
        entry["proven_at"] = previous["proven_at"]
    return entry


def _witness_detail(host: str) -> dict[str, Any]:
    """Attest the host's invoked projection against the fix registry (AR-363).

    Never raises: the battery must still seal its receipt when the witness
    layer itself fails, and that failure is reported as unavailable rather
    than counted as a pass.
    """

    try:
        return attest_host(host).as_dict()
    except Exception as error:
        return {
            "status": "unavailable",
            "reason_code": "witness_error",
            "reason": type(error).__name__,
        }


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
    trials: int | None = None,
) -> dict[str, Any]:
    """Observe versions, run the graded battery for changed harnesses, seal receipts.

    Version observation and the posture scan stay single-shot and
    deterministic; only the host turn (canary or ordinary) is the graded,
    repeated check. ``trials`` is the per-probe ``k`` (AR-360).
    """

    if canary_runner is None:
        from agency_runtime.core.canary import run_canary as canary_runner
    trials_per_probe = validated_trials(trials)
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
        if store_factory is None and probe_mode(host) == "ordinary":
            # Load the configuration once for every ordinary host in this run.
            store_factory = _default_store_factory(config_path)
        probe = _host_probe(
            host,
            canary_runner=canary_runner,
            config_path=config_path,
            store_factory=store_factory,
            resolver=resolver,
            runner=runner,
        )
        outcome, detail = _run_graded_probe(host, trials=trials_per_probe, probe=probe)
        detail["posture"] = posture
        # A passing canary on stale hooks proves nothing about the shipped
        # fixes; the witness verdict fails the host (AR-363).
        detail["witness"] = witness = _witness_detail(host)
        if outcome == "passed" and witness.get("status") in WITNESS_FAILURE_STATUSES:
            outcome = detail["outcome"] = "failed"
            detail["reason"] = "deployed_fix_witness_failed"
        detail["observed_version"] = observed[host]
        detail["ran_at"] = _now()
        receipt = _write_receipt(receipts, host, detail)
        document["harnesses"][host] = _fingerprint_entry(
            document["harnesses"].get(host),
            outcome=outcome,
            detail=detail,
            observed_version=observed[host],
            receipt=receipt,
        )
        results[host] = detail
    if due:
        _write_fingerprints(document, fingerprint_file)
    failed = [host for host, detail in results.items() if detail["outcome"] != "passed"]
    return {
        "schema": BATTERY_SCHEMA,
        "observed": observed,
        "ran": list(due),
        "trials": trials_per_probe,
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
    re-adopt explicitly after proving harnesses by other means. Hosts whose
    version cannot be observed are reported under ``skipped`` with a
    names-only reason so an empty adoption is diagnosable, never silent
    (AR-340).
    """

    selected = tuple(hosts) if hosts else BATTERY_HOSTS
    for host in selected:
        if host not in BATTERY_HOSTS:
            raise ValueError(f"unsupported battery harness: {host}")
    fingerprint_file = fingerprint_path or default_fingerprint_path()
    document = read_fingerprints(fingerprint_file)
    adopted: dict[str, str] = {}
    skipped: dict[str, str] = {}
    stamp = _now()
    for host in selected:
        version, reason = observe_harness_version_detail(host, resolver=resolver, runner=runner)
        if not version:
            skipped[host] = reason
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
    return {"schema": BATTERY_SCHEMA, "baseline": adopted, "skipped": skipped}


def describe_result(host: str, detail: Mapping[str, Any]) -> str:
    """One human line per host: outcome, grading tally, reason, and version.

    Example: ``hermes: passed (pass@2: 1/2 trials) (Hermes Agent v0.21.0)``.
    """

    grading = detail.get("grading")
    notes: list[str] = []
    if isinstance(grading, Mapping):
        label = grading_label(
            str(grading.get("mode") or ""),
            int(grading.get("trials_requested") or 0),
        )
        passed = len(grading.get("passed_trials") or ())
        notes.append(f"{label}: {passed}/{int(grading.get('trials_run') or 0)} trials")
    reason = str(detail.get("reason") or "")
    if reason:
        notes.append(reason)
    summary = f" ({'; '.join(notes)})" if notes else ""
    return f"{host}: {detail['outcome']}{summary} ({detail['observed_version']})"


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
            for host, reason in sorted(report.get("skipped", {}).items()):
                print(f"{host}: skipped ({reason})")
            if not report["baseline"]:
                print("harness battery: no harness version could be adopted")
        return 0 if report["baseline"] else 1
    report = run_battery(
        hosts=hosts,
        force=bool(getattr(args, "force", False)),
        config_path=getattr(args, "config", None),
        trials=getattr(args, "trials", None),
    )
    if getattr(args, "json", False):
        print(json.dumps(report, indent=1, sort_keys=True))
    elif not report["ran"]:
        print("harness battery: no harness version change detected")
    else:
        for host in report["ran"]:
            print(describe_result(host, report["results"][host]))
    return 0 if report["ok"] else 1
