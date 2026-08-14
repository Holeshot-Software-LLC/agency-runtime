"""Rule 5 at the source: only the host may start an agent.

The eval under test proves a separation rather than an absence. Agency starts
processes legitimately and often -- inference providers, installers, git, the
host canary -- so counting process-capable modules proves nothing. What must
hold is that the code which can start a process and the code which can bring a
worker into Agency's records never meet.

These cases do two jobs. They assert the separation holds in the shipped
package, and they prove the analysis would fail if it stopped holding: a
detector that cannot fail is decoration, not evidence.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from agency_runtime.core.evals.spawn_authority import (
    _HOST_BOUNDARY_MODULES,
    analyze_package,
    analyze_source,
    run_spawn_authority_eval,
)

_VIOLATION = (
    "from agency_runtime.core.owned_process import run_bounded_process\n"
    "\n"
    "def dispatch(store, task):\n"
    "    process = run_bounded_process(['claude', '-p', task])\n"
    "    store.record_native_child_started(worker_id=process.pid)\n"
    "    return process\n"
)
_ONLY_STARTS_A_PROCESS = (
    "from agency_runtime.core.owned_process import run_bounded_process\n"
    "\n"
    "def probe(argv):\n"
    "    return run_bounded_process(argv)\n"
)
_ONLY_CREATES_A_WORKER = (
    "def adopt(store, agent_id):\n"
    "    return store.record_native_child_started(worker_id=agent_id)\n"
)


def _case(report: dict[str, object], name: str) -> dict[str, object]:
    cases = report["cases"]
    assert isinstance(cases, list)
    for case in cases:
        if case["name"] == name:
            return dict(case)
    raise AssertionError(f"eval reported no case named {name}")


@pytest.fixture
def shipped_copy(tmp_path: Path) -> Path:
    """A writable copy of the shipped package, for injecting a violation."""

    import agency_runtime

    source = Path(str(agency_runtime.__file__)).resolve().parent
    target = tmp_path / "agency_runtime"
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return target


def test_the_shipped_package_never_lets_agency_start_an_agent() -> None:
    report = run_spawn_authority_eval()
    failures = [case for case in report["cases"] if not case["passed"]]
    assert failures == [], failures
    assert report["passed"] is True

    disjoint = _case(report, "starting_a_process_is_disjoint_from_creating_a_worker")
    detail = disjoint["detail"]
    assert isinstance(detail, dict)
    assert detail["overlap"] == 0
    # Guard the detectors themselves: an empty side would make the claim vacuous.
    assert detail["process_capable"] > 0
    assert detail["worker_origin"] > 0


def test_a_module_that_starts_a_process_and_creates_a_worker_fails_the_eval(
    shipped_copy: Path,
) -> None:
    """The headline control: prove the separation check can actually fail."""

    (shipped_copy / "core" / "rogue_dispatcher.py").write_text(_VIOLATION, encoding="utf-8")

    report = run_spawn_authority_eval(shipped_copy)

    assert report["passed"] is False
    disjoint = _case(report, "starting_a_process_is_disjoint_from_creating_a_worker")
    assert disjoint["passed"] is False
    assert "agency_runtime.core.rogue_dispatcher" in str(disjoint["error"])
    assert "decide to spawn" in str(disjoint["error"])


def test_a_worker_created_outside_a_host_boundary_fails_the_eval(shipped_copy: Path) -> None:
    (shipped_copy / "core" / "quiet_adopter.py").write_text(
        _ONLY_CREATES_A_WORKER, encoding="utf-8"
    )

    report = run_spawn_authority_eval(shipped_copy)

    assert report["passed"] is False
    confinement = _case(report, "worker_origin_is_confined_to_host_boundaries")
    assert confinement["passed"] is False
    assert "agency_runtime.core.quiet_adopter" in str(confinement["error"])


def test_an_undeclared_process_module_fails_the_eval(shipped_copy: Path) -> None:
    """A new way to start a process is unproven until somebody classifies it."""

    (shipped_copy / "core" / "new_prober.py").write_text(_ONLY_STARTS_A_PROCESS, encoding="utf-8")

    report = run_spawn_authority_eval(shipped_copy)

    assert report["passed"] is False
    purposes = _case(report, "every_process_module_declares_a_tool_purpose")
    assert purposes["passed"] is False
    assert "agency_runtime.core.new_prober" in str(purposes["error"])
    # The separation itself still holds -- the new module starts no worker.
    assert _case(report, "starting_a_process_is_disjoint_from_creating_a_worker")["passed"] is True


def test_a_seam_reference_that_is_never_called_is_still_detected() -> None:
    """The shape a call-only detector misses, and the reason this one differs.

    ``cli_transport`` never calls ``run_bounded_process``. It passes it as a
    default argument and calls it through the injected name.
    """

    facts = analyze_source(
        "injected",
        "from agency_runtime.core.owned_process import run_bounded_process\n"
        "def go(argv, runner=run_bounded_process):\n"
        "    return runner(argv)\n",
    )
    assert facts.starts_process is True

    shipped = analyze_package()
    assert shipped["agency_runtime.core.cli_transport"].starts_process is True


def test_an_unrelated_run_method_is_not_mistaken_for_a_process_seam() -> None:
    facts = analyze_source(
        "unrelated",
        "class Job:\n    def run(self):\n        return 1\n\ndef go(job):\n    return job.run()\n",
    )
    assert facts.starts_process is False


def test_an_aliased_stdlib_seam_is_detected() -> None:
    facts = analyze_source(
        "aliased",
        "from subprocess import Popen as _Launch\ndef go(argv):\n    return _Launch(argv)\n",
    )
    assert facts.starts_process is True


def test_every_declared_host_boundary_still_creates_a_worker() -> None:
    """Guard against a rename quietly emptying the worker side of the claim."""

    shipped = analyze_package()
    for name in sorted(_HOST_BOUNDARY_MODULES):
        assert name in shipped, f"{name} is no longer a shipped module"
        assert shipped[name].creates_worker is True, f"{name} no longer creates a worker"
        assert shipped[name].starts_process is False, f"{name} gained a process seam"
