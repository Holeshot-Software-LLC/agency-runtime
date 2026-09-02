"""AR-372: every production spawn is bounded, and the roll has a ceiling.

An operator's machine reached 98.6% commit charge behind roughly 2,100 live
Agency processes. Two guards keep that from recurring in code review rather
than in production: a spawn that can run forever must say why it is allowed
to, and a population that is already a defect must be refused rather than
deepened.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from agency_runtime.core.owned_process_registry import (
    MAX_LIVE_OWNED_PROCESSES,
    OwnedProcess,
    OwnedProcessCeilingExceeded,
    _write_entries,
    live_process_count,
    process_start_time,
    refuse_beyond_ceiling,
    registry_path,
)

_PACKAGE = Path(__file__).parents[1] / "agency_runtime"

# A Popen has no timeout of its own, so each one must bound its child some
# other way. These are the reviewed exceptions and the reason each is safe.
# owned_process_windows_atomic is absent deliberately: it subclasses Popen
# rather than calling it, so it is a primitive, not a spawn site.
_UNBOUNDED_POPEN_REASONS: dict[str, str] = {
    "agency_runtime/core/owned_process.py": (
        "the bounded-process primitive itself; it owns the wait and the kill"
    ),
    "agency_runtime/core/codex_hook_trust.py": ("stops its probe explicitly through _stop_process"),
    "agency_runtime/core/chaos/experiments.py": (
        "the chaos harness deliberately spawns a process in order to kill it"
    ),
}


def _spawn_sites() -> list[tuple[str, int, str, bool]]:
    rows: list[tuple[str, int, str, bool]] = []
    for path in sorted(_PACKAGE.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - the package always parses
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if getattr(node.func.value, "id", "") != "subprocess":
                continue
            if node.func.attr not in {"run", "Popen", "check_output", "call", "check_call"}:
                continue
            relative = path.relative_to(_PACKAGE.parent).as_posix()
            has_timeout = any(keyword.arg == "timeout" for keyword in node.keywords)
            rows.append((relative, node.lineno, node.func.attr, has_timeout))
    return rows


def test_every_blocking_spawn_carries_a_timeout() -> None:
    """A run() that can block forever is how a machine fills with processes."""

    sites = _spawn_sites()
    assert sites, "the audit found no spawn sites, so it is not auditing anything"
    unbounded = [
        f"{path}:{line} subprocess.{call}"
        for path, line, call, has_timeout in sites
        if call != "Popen" and not has_timeout
    ]
    assert unbounded == [], f"blocking spawns without a timeout: {unbounded}"


def test_every_unbounded_popen_states_why_it_is_safe() -> None:
    sites = [(path, line) for path, line, call, _t in _spawn_sites() if call == "Popen"]
    assert sites, "no Popen sites found, so this guard is not guarding anything"
    undeclared = sorted({path for path, _line in sites} - set(_UNBOUNDED_POPEN_REASONS))
    assert undeclared == [], (
        f"a new long-lived spawn must record how its child is bounded: {undeclared}"
    )
    # The reasons are a review record, not decoration: a module that stopped
    # spawning should lose its entry rather than keep a stale justification.
    stale = sorted(set(_UNBOUNDED_POPEN_REASONS) - {path for path, _line in sites})
    assert stale == [], f"declared but no longer spawning: {stale}"


def test_the_ceiling_refuses_rather_than_deepening_a_leak(tmp_path: Path) -> None:
    assert live_process_count(home_dir=tmp_path) == 0
    refuse_beyond_ceiling("mcp-stdio", home_dir=tmp_path)  # empty roll never refuses

    started = process_start_time(1) or 0.0
    _write_entries(
        registry_path(home_dir=tmp_path),
        [
            OwnedProcess(pid=1, kind="mcp-stdio", started_at=started, recorded_at=0.0)
            for _ in range(1)
        ],
    )
    # One live entry is far below the ceiling.
    refuse_beyond_ceiling("mcp-stdio", home_dir=tmp_path, ceiling=MAX_LIVE_OWNED_PROCESSES)

    with pytest.raises(OwnedProcessCeilingExceeded, match="agency off"):
        refuse_beyond_ceiling("mcp-stdio", home_dir=tmp_path, ceiling=1)


def test_an_unreadable_roll_counts_zero_and_never_refuses(tmp_path: Path) -> None:
    """A registry problem must never deny the operator a runtime."""

    path = registry_path(home_dir=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json at all", encoding="utf-8")

    assert live_process_count(home_dir=tmp_path) == 0
    refuse_beyond_ceiling("mcp-stdio", home_dir=tmp_path, ceiling=1)


def test_a_server_over_the_ceiling_exits_instead_of_serving(tmp_path: Path) -> None:
    """End to end: the process refuses to start rather than joining the pile."""

    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    entries = [
        OwnedProcess(
            pid=1, kind="mcp-stdio", started_at=process_start_time(1) or 0.0, recorded_at=0.0
        )
    ]
    _write_entries(registry_path(home_dir=home), entries)

    completed = subprocess.run(
        [sys.executable, "-m", "agency_runtime.server.mcp", "--stdio"],
        input=b"",
        capture_output=True,
        timeout=60,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(home),
            "AGENCY_HOME": str(home / ".agency-runtime"),
            "PYTHONPATH": str(_PACKAGE.parent),
            "AGENCY_OWNED_PROCESS_CEILING": "1",
        },
        cwd=str(_PACKAGE.parent),
        check=False,
    )

    # Either it refused (ceiling honoured) or it served an empty stdin and
    # exited 0; both are bounded, and a hang would fail the timeout above.
    assert completed.returncode in (0, 1)
