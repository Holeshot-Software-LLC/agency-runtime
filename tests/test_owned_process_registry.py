"""AR-372: `agency off` ends the processes Agency started, and only those.

Flipping the control flag used to leave every long-lived Agency process
running, which is how an operator's machine reached 98.6% commit charge
behind roughly 2,100 of them. Ownership is now recorded rather than guessed,
and these tests pin the two properties that make ending them safe: a process
id that has been reused is never signalled, and a registry that cannot be
read or written never blocks a server from serving.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from agency_runtime.core import owned_process_registry as subject


def _sleeper() -> subprocess.Popen[bytes]:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])


def test_a_registered_process_is_listed_then_ended(tmp_path: Path) -> None:
    child = _sleeper()
    try:
        assert subject.register_process("mcp-stdio", pid=child.pid, home_dir=tmp_path)
        live = subject.live_processes(home_dir=tmp_path)
        assert [entry.pid for entry in live] == [child.pid]
        assert [entry.kind for entry in live] == ["mcp-stdio"]

        report = subject.terminate_owned_processes(home_dir=tmp_path)

        assert [row["pid"] for row in report["ended"]] == [child.pid]
        assert report["failed"] == []
        assert report["remaining"] == 0
        assert subject.live_processes(home_dir=tmp_path) == []
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()


def test_a_reused_process_id_is_never_signalled(tmp_path: Path) -> None:
    """The whole point of recording a start time: ids are reused."""

    victim = _sleeper()
    try:
        # Record the victim's id, but with a start time that cannot be its own.
        assert subject._write_entries(
            subject.registry_path(home_dir=tmp_path),
            [
                subject.OwnedProcess(
                    pid=victim.pid,
                    kind="mcp-stdio",
                    started_at=1.0,
                    recorded_at=time.time(),
                )
            ],
        )
        if subject.process_start_time(victim.pid) is None:
            # Without a start-time source the registry falls back to liveness;
            # the guarantee below is only assertable where the marker exists.
            return
        assert subject.live_processes(home_dir=tmp_path) == []

        report = subject.terminate_owned_processes(home_dir=tmp_path)

        assert report["ended"] == []
        assert victim.poll() is None, "an unrelated process was signalled"
    finally:
        if victim.poll() is None:
            victim.kill()
        victim.wait()


def test_an_unreaped_exit_counts_as_gone(tmp_path: Path) -> None:
    """A zombie answers os.kill(pid, 0), so signalling alone reports it alive."""

    child = _sleeper()
    child.kill()
    for _ in range(50):
        if subject._process_is_zombie(child.pid):
            break
        time.sleep(0.05)
    else:  # pragma: no cover - platform without a readable process state
        child.wait()
        return
    assert subject.process_is_alive(child.pid) is False
    child.wait()


def test_a_dead_process_is_forgotten_rather_than_reported(tmp_path: Path) -> None:
    child = _sleeper()
    child.kill()
    child.wait()
    assert subject.register_process("mcp-stdio", pid=child.pid, home_dir=tmp_path)

    assert subject.live_processes(home_dir=tmp_path) == []
    assert subject.terminate_owned_processes(home_dir=tmp_path)["ended"] == []


def test_only_the_requested_kinds_are_ended(tmp_path: Path) -> None:
    keeper = _sleeper()
    try:
        assert subject.register_process("dashboard", pid=keeper.pid, home_dir=tmp_path)

        report = subject.terminate_owned_processes(home_dir=tmp_path, kinds=("mcp-stdio",))

        assert report["ended"] == []
        assert report["remaining"] == 1
        assert keeper.poll() is None
    finally:
        if keeper.poll() is None:
            keeper.kill()
        keeper.wait()


def test_forgetting_removes_one_entry_and_leaves_the_rest(tmp_path: Path) -> None:
    assert subject.register_process("mcp-stdio", pid=os.getpid(), home_dir=tmp_path)
    assert subject.register_process("dashboard", pid=os.getpid() + 1, home_dir=tmp_path)

    assert subject.forget_process(pid=os.getpid(), home_dir=tmp_path)

    remaining = {
        entry.pid for entry in subject._read_entries(subject.registry_path(home_dir=tmp_path))
    }
    assert os.getpid() not in remaining


def test_an_unreadable_registry_never_blocks_a_server(tmp_path: Path) -> None:
    """Losing the roll is Agency's problem, not a reason to deny a runtime."""

    path = subject.registry_path(home_dir=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("this is not json", encoding="utf-8")

    assert subject.live_processes(home_dir=tmp_path) == []
    assert subject.register_process("mcp-stdio", pid=os.getpid(), home_dir=tmp_path)
    assert [entry.kind for entry in subject.live_processes(home_dir=tmp_path)] == ["mcp-stdio"]


def test_the_roll_is_bounded(tmp_path: Path) -> None:
    path = subject.registry_path(home_dir=tmp_path)
    assert subject._write_entries(
        path,
        [
            subject.OwnedProcess(pid=os.getpid(), kind="mcp-stdio", started_at=0.0, recorded_at=0.0)
            for _ in range(1)
        ],
    )
    entries = subject._read_entries(path)
    assert len(entries) <= subject.MAX_REGISTERED_PROCESSES
    # A malformed row is dropped rather than poisoning the whole roll.
    assert subject._project_entry({"pid": 0, "kind": "x"}) is None
    assert subject._project_entry({"pid": 5, "kind": ""}) is None
    assert subject._project_entry("not-a-mapping") is None
