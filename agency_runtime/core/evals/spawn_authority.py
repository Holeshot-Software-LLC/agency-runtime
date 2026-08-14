"""Rule 5 at the source: Agency never decides to spawn.

Rule 5 says spawning is the native harness's call, always, and that Agency's job
is to staff whoever exists.  Proving that at the source is not a reachability
sweep for ``subprocess``: Agency legitimately starts processes all the time.  It
shells out to CLI inference providers, installs host adapters, runs git, probes
a host canary, and updates itself, all through the same hardened bounded-process
primitive.  Counting how many process-capable modules a turn can reach therefore
measures nothing -- an earlier formulation of this proof counted sixteen and had
to be withdrawn.

The distinction the rule actually draws is between a **tool** and an **agent**.
A tool is started, returns a value, and is gone: an install result, a git
output, a routing answer.  An agent is a worker -- it gets an identity, a
lifecycle, and a unit of the user's work.  Agency may start tools.  Only the
host may start agents.

So this eval proves a separation rather than an absence:

* the modules that can start an operating-system process, and the modules that
  can bring a worker into Agency's records, are **disjoint**;
* worker origin is confined to the host boundaries and the store table that
  persists what a host reported, so a worker identity can only enter Agency
  from a host;
* every process-capable module is declared with an explicit tool purpose, so a
  new one fails this eval until somebody classifies it.

Agency therefore has no path by which a process it starts becomes an agent.

The seam detector counts a *reference*, not just a call.  ``cli_transport``
never calls ``run_bounded_process``; it passes it as a default argument and
calls it through the injected name, which a call-only detector misses entirely.
Over-approximating the process side only makes the disjointness claim stronger.
Two positive controls prove the analysis fires: a module that does both things
must be flagged, and the default-argument shape must be detected.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Final

# Agency's own process seams, plus the standard-library primitives underneath
# them.  A bare name counts only when it was imported from one of the modules
# below, so an unrelated local helper called ``run`` is not mistaken for one.
_AGENCY_SEAMS: Final[frozenset[str]] = frozenset(
    {
        "run_bounded_process",
        "run_bounded_binary_process",
        "_spawn_owned_process",
        "_spawn_owned_binary_process",
    }
)
_STDLIB_SEAMS: Final[dict[str, frozenset[str]]] = {
    "subprocess": frozenset({"Popen", "run", "call", "check_call", "check_output"}),
    "os": frozenset(
        {
            "system",
            "popen",
            "execv",
            "execve",
            "execvp",
            "execvpe",
            "spawnv",
            "spawnve",
            "spawnvp",
            "posix_spawn",
            "posix_spawnp",
            "fork",
            "forkpty",
        }
    ),
    "multiprocessing": frozenset({"Process"}),
}

# Every call that brings a worker into Agency's records: an identity, a
# lifecycle transition, or a staffing decision bound to one.
_WORKER_ORIGIN_CALLS: Final[frozenset[str]] = frozenset(
    {
        "_native_child_identity",
        "_record_native_child_lifecycle",
        "record_native_child_started",
        "record_native_child_stopped",
        "record_native_child_ended",
        "record_native_child_staffing_decision",
        "staff_native_child",
    }
)

# Worker origin belongs to the host boundaries and to the one store table that
# persists what a host reported.  Nothing else may create a worker.
_HOST_BOUNDARY_MODULES: Final[frozenset[str]] = frozenset(
    {
        "agency_runtime.adapters.base",
        "agency_runtime.adapters.hermes.bridge",
        "agency_runtime.adapters.hooks",
        "agency_runtime.adapters.openclaw.node_bridge",
        "agency_runtime.core.store.native_child",
    }
)

# Every module that can start a process, and the tool purpose it starts one for.
# None of these is a host boundary, and none of them may create a worker.  A new
# process-capable module fails this eval until it is classified here.
_DECLARED_PROCESS_PURPOSES: Final[dict[str, str]] = {
    "agency_runtime.core.canary_backends": "host canary probe",
    "agency_runtime.core.cli_transport": "inference provider call",
    "agency_runtime.core.codex_hook_trust": "host hook-trust inspection",
    "agency_runtime.core.dashboard_service_core": "operator dashboard",
    "agency_runtime.core.delegation.backend_process_compat": "bounded-process compatibility",
    "agency_runtime.core.delegation.backends": "bounded-process compatibility",
    "agency_runtime.core.evals.benchmarks": "evaluation harness",
    "agency_runtime.core.evals.decision_conformance": "evaluation harness",
    "agency_runtime.core.evals.product_host": "evaluation harness",
    "agency_runtime.core.evals.product_validation": "evaluation harness",
    "agency_runtime.core.git_runner": "git command",
    "agency_runtime.core.installed_config_compatibility": "installed config probe",
    "agency_runtime.core.installer_native": "host adapter install",
    "agency_runtime.core.installer_uninstall": "host adapter uninstall",
    "agency_runtime.core.owned_process": "bounded-process primitive",
    "agency_runtime.core.owned_process_linux": "bounded-process primitive",
    "agency_runtime.core.owned_process_windows": "bounded-process primitive",
    "agency_runtime.core.owned_process_windows_atomic": "bounded-process primitive",
    "agency_runtime.core.prepared_codex_install": "host adapter install",
    "agency_runtime.core.smoke": "operator smoke check",
    "agency_runtime.core.update_service": "runtime self-update",
}


class _ModuleFacts:
    """What one module can do, read from its syntax alone."""

    def __init__(self, name: str, tree: ast.Module) -> None:
        self.name = name
        self._seam_aliases: set[str] = set()
        self._module_aliases: dict[str, str] = {}
        self.starts_process = False
        self.worker_origin_calls: set[str] = set()
        self._read(tree)

    def _record_import(self, node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _STDLIB_SEAMS:
                    self._module_aliases[alias.asname or root] = root
            return
        source = (node.module or "").split(".")[-1]
        for alias in node.names:
            local = alias.asname or alias.name
            from_stdlib_seam = source in _STDLIB_SEAMS and alias.name in _STDLIB_SEAMS[source]
            if alias.name in _AGENCY_SEAMS or from_stdlib_seam:
                self._seam_aliases.add(local)
            elif alias.name in _STDLIB_SEAMS:
                self._module_aliases[local] = alias.name

    def _read(self, tree: ast.Module) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._record_import(node)
        for node in ast.walk(tree):
            # A reference is enough.  Passing a seam as a default argument and
            # calling it through the injected name still starts a process.
            if isinstance(node, ast.Name):
                if node.id in _AGENCY_SEAMS or node.id in self._seam_aliases:
                    self.starts_process = True
            elif isinstance(node, ast.Attribute):
                if node.attr in _AGENCY_SEAMS:
                    self.starts_process = True
                value = node.value
                if isinstance(value, ast.Name):
                    root = self._module_aliases.get(value.id, value.id)
                    if node.attr in _STDLIB_SEAMS.get(root, frozenset()):
                        self.starts_process = True
            if isinstance(node, ast.Call):
                func = node.func
                called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                if called in _WORKER_ORIGIN_CALLS:
                    self.worker_origin_calls.add(called)

    @property
    def creates_worker(self) -> bool:
        return bool(self.worker_origin_calls)


def _module_name(root: Path, path: Path) -> str:
    parts = (root.name, *path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _package_root() -> Path:
    """Analyze the shipped package, wherever it is installed from."""

    import agency_runtime

    location = getattr(agency_runtime, "__file__", "")
    if not location:
        raise AssertionError("agency_runtime package location is unavailable")
    return Path(location).resolve().parent


def analyze_package(root: Path | None = None) -> dict[str, _ModuleFacts]:
    """Read every shipped module's process and worker-origin capability."""

    package_root = root if root is not None else _package_root()
    facts: dict[str, _ModuleFacts] = {}
    for path in sorted(package_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
            raise AssertionError(f"{path} could not be parsed: {exc}") from exc
        name = _module_name(package_root, path)
        facts[name] = _ModuleFacts(name, tree)
    if not facts:
        raise AssertionError("no shipped modules were analyzed")
    return facts


def analyze_source(name: str, source: str) -> _ModuleFacts:
    """Read one module's capability from source text, for the positive controls."""

    return _ModuleFacts(name, ast.parse(source, filename=f"<{name}>"))


def _require(condition: object, message: str) -> None:
    """Fail one deterministic eval independently of Python optimization flags."""

    if not condition:
        raise AssertionError(message)


def _named(values: Iterable[str]) -> str:
    return ", ".join(sorted(values))


def _process_modules(facts: dict[str, _ModuleFacts]) -> set[str]:
    return {name for name, fact in facts.items() if fact.starts_process}


def _worker_modules(facts: dict[str, _ModuleFacts]) -> set[str]:
    return {name for name, fact in facts.items() if fact.creates_worker}


def _case_starting_a_process_is_disjoint_from_creating_a_worker(
    root: Path | None = None,
) -> dict[str, Any]:
    """The rule itself: no module can both start a process and create a worker."""

    facts = analyze_package(root)
    processes = _process_modules(facts)
    workers = _worker_modules(facts)
    overlap = processes & workers
    _require(
        not overlap,
        "a module both starts a process and creates a worker, so Agency can "
        f"decide to spawn an agent: {_named(overlap)}",
    )
    _require(processes, "no process-capable module was found, so the seam detector is broken")
    _require(workers, "no worker-origin module was found, so the worker detector is broken")
    return {
        "modules": len(facts),
        "process_capable": len(processes),
        "worker_origin": len(workers),
        "overlap": 0,
    }


def _case_worker_origin_is_confined_to_host_boundaries(
    root: Path | None = None,
) -> dict[str, Any]:
    """A worker can only enter Agency's records at a host boundary."""

    facts = analyze_package(root)
    workers = _worker_modules(facts)
    unexpected = workers - _HOST_BOUNDARY_MODULES
    _require(
        not unexpected,
        "a module outside the host boundaries creates a worker, so Agency can "
        f"staff someone the host never started: {_named(unexpected)}",
    )
    missing = _HOST_BOUNDARY_MODULES - workers
    _require(
        not missing,
        "a declared host boundary no longer creates a worker, so this eval is "
        f"guarding a path that moved: {_named(missing)}",
    )
    return {"host_boundaries": sorted(workers)}


def _case_every_process_module_declares_a_tool_purpose(
    root: Path | None = None,
) -> dict[str, Any]:
    """A new process-capable module fails until somebody classifies it."""

    facts = analyze_package(root)
    processes = _process_modules(facts)
    undeclared = processes - set(_DECLARED_PROCESS_PURPOSES)
    _require(
        not undeclared,
        "a module starts a process for an undeclared purpose; classify it as a "
        f"tool or Rule 5 is unproven: {_named(undeclared)}",
    )
    departed = set(_DECLARED_PROCESS_PURPOSES) - processes
    _require(
        not departed,
        f"a declared process-capable module no longer starts one: {_named(departed)}",
    )
    overlap = set(_DECLARED_PROCESS_PURPOSES) & _HOST_BOUNDARY_MODULES
    _require(
        not overlap,
        f"a host boundary is declared as a process starter: {_named(overlap)}",
    )
    return {"declared": len(_DECLARED_PROCESS_PURPOSES)}


def _case_control_a_module_doing_both_is_detected(
    root: Path | None = None,
) -> dict[str, Any]:
    """Positive control: prove the disjointness check would fire."""

    facts = analyze_source(
        "control.spawns_a_worker",
        "from agency_runtime.core.owned_process import run_bounded_process\n"
        "def go(store, payload):\n"
        "    process = run_bounded_process(['claude', '-p', payload['task']])\n"
        "    store.record_native_child_started(worker_id=process.pid)\n",
    )
    _require(facts.starts_process, "the control module was not seen to start a process")
    _require(facts.creates_worker, "the control module was not seen to create a worker")
    return {"detected": sorted(facts.worker_origin_calls)}


def _case_control_an_uncalled_seam_reference_is_detected(
    root: Path | None = None,
) -> dict[str, Any]:
    """Positive control: the shape a call-only detector misses.

    ``cli_transport`` never calls the seam.  It passes it as a default argument
    and calls it through the injected name.
    """

    facts = analyze_source(
        "control.injected_runner",
        "from agency_runtime.core.owned_process import run_bounded_process\n"
        "def go(argv, runner=run_bounded_process):\n"
        "    return runner(argv)\n",
    )
    _require(
        facts.starts_process,
        "a seam passed as a default argument was not detected, so the process "
        "side is under-approximated and the disjointness claim is hollow",
    )
    unrelated = analyze_source(
        "control.unrelated_run",
        "class Job:\n    def run(self):\n        return 1\n\ndef go(job):\n    return job.run()\n",
    )
    _require(
        not unrelated.starts_process,
        "an unrelated method named run was mistaken for a process seam",
    )
    return {"detected": True}


def _run_case(
    name: str,
    fn: Callable[[Path | None], dict[str, Any] | None],
    root: Path | None,
) -> dict[str, Any]:
    try:
        detail = fn(root) or {}
        return {"name": name, "passed": True, "detail": detail}
    except AssertionError as exc:
        return {"name": name, "passed": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive harness boundary
        return {"name": name, "passed": False, "error": f"{type(exc).__name__}: {exc}"}


def run_spawn_authority_eval(root: Path | None = None) -> dict[str, Any]:
    """Run the deterministic Rule 5 spawn-authority eval suite.

    ``root`` analyzes a different package tree, which is how the tests prove
    this suite actually fails when the separation is broken.
    """

    cases = [
        (
            "starting_a_process_is_disjoint_from_creating_a_worker",
            _case_starting_a_process_is_disjoint_from_creating_a_worker,
        ),
        (
            "worker_origin_is_confined_to_host_boundaries",
            _case_worker_origin_is_confined_to_host_boundaries,
        ),
        (
            "every_process_module_declares_a_tool_purpose",
            _case_every_process_module_declares_a_tool_purpose,
        ),
        (
            "control_a_module_doing_both_is_detected",
            _case_control_a_module_doing_both_is_detected,
        ),
        (
            "control_an_uncalled_seam_reference_is_detected",
            _case_control_an_uncalled_seam_reference_is_detected,
        ),
    ]
    results = [_run_case(name, fn, root) for name, fn in cases]
    passed = sum(1 for case in results if case["passed"])
    return {
        "suite": "spawn-authority",
        "passed": passed == len(results),
        "passed_count": passed,
        "failed_count": len(results) - passed,
        "cases": results,
    }


__all__ = ["analyze_package", "analyze_source", "run_spawn_authority_eval"]
