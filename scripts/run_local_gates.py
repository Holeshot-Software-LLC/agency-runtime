"""Run the gates CI used to run on every push to main.

Push no longer triggers `.github/workflows/ci.yml`, because this repository is
developed direct-to-main and every commit started a 7-10 minute hosted run --
which the workflow's own concurrency group then cancelled mid-flight when the
next commit landed, billing both. This script is the replacement: it runs the
same commands as the workflow's `quality-contracts` job, in the same order, and
fails on the first gate that fails.

    python scripts/run_local_gates.py            # everything runnable here
    python scripts/run_local_gates.py --fast     # skip the two long suites
    python scripts/run_local_gates.py --list     # show the gates and exit

Two deliberate differences from the hosted job, both reported rather than
hidden:

* `eval decision-conformance` cannot run its mutation phase on a machine whose
  pytest lives in user site-packages, because the sandbox redirects HOME. This
  script substitutes a direct check that every mutation's `before` snippet still
  matches its source exactly once, which is what actually breaks when someone
  edits a guarded line.
* The hosted job runs on Linux. Anything platform-sensitive still needs
  `gh workflow run ci.yml` or a WSL run.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parent.parent

# The single source for the "Run fast Python production spine" step in ci.yml
# and the Validation block in AGENTS.md; tests/test_release_packaging.py derives
# both expectations from this tuple rather than pinning further copies. Three
# hand-kept copies had already drifted: AGENTS.md was missing two entries.
PRODUCTION_SPINE = (
    "tests/test_senior_audit_hardening.py",
    "tests/test_configuration_namespace_security.py",
    "tests/test_executable_namespace_security.py",
    "tests/test_storage_file_trust.py",
    "tests/test_dashboard_auth_boundary_regression.py",
    "tests/test_dashboard_transaction_refactors.py",
    "tests/test_routing_correctness.py",
    "tests/test_workforce_hiring_contract.py",
    "tests/test_workforce_selection_safety.py",
    "tests/test_workforce_dynamic_hiring.py",
    "tests/test_upstream_selection_eval.py",
    "tests/test_decision_conformance.py",
    "tests/test_delegation_p1_correctness.py",
    "tests/test_store_turn_atomicity.py",
    "tests/test_roster_snapshot_generation.py",
    "tests/test_mcp_protocol_hardening.py",
    "tests/test_cli_parser_contract.py",
    "tests/test_cli_upgrade.py",
    "tests/test_update_service.py",
    "tests/test_native_installer.py",
    "tests/test_host_uninstall.py",
    "tests/test_cli_uninstall.py",
    "tests/test_host_boundary_hardening.py",
    "tests/test_cli_owner_authority.py",
    "tests/test_security_turn_boundaries.py",
    # Canary record contracts. Two of these files asserted contradictory exit
    # codes for the same protocol error, and the contradiction sat red on main
    # because neither ran here.
    "tests/test_canary_coverage_complete.py",
    "tests/test_complexity_refactors.py",
    # AR-354: the host-CLI coverage suite and the persistent-host lifecycle
    # suite sat red on main for weeks because neither ran here.
    "tests/test_coverage_final_host_cli.py",
    "tests/test_resident_manager_lifecycle.py",
)

# Kept identical to the "Run AR-119 matrix evidence" step in ci.yml. That list
# is asserted equal to the matrix citations by tests/test_release_packaging.py,
# so it changes only when the matrix does.
MATRIX_EVIDENCE = (
    "tests/test_accepted_outcomes.py",
    "tests/test_adapter_parity.py",
    "tests/test_child_delivery_evidence.py",
    "tests/test_codex_plaintext_hook.py",
    "tests/test_codex_spawn_provenance.py",
    "tests/test_completion_policy_boundary.py",
    "tests/test_contractor_minting_host_parity.py",
    "tests/test_host_canary.py",
    "tests/test_host_hooks.py",
    "tests/test_host_parity_eval.py",
    "tests/test_jit_staffing_host_parity.py",
    "tests/test_native_child_adapter_staffing.py",
    "tests/test_native_child_host_boundary_staffing.py",
    "tests/test_parent_caller_card_delivery.py",
    "tests/test_spawn_origin_absence.py",
)

WORKFLOW_CONTRACTS = (
    "tests/test_ci_change_scope.py",
    "tests/test_ci_sharding.py",
    "tests/test_ci_session_pair.py",
    "tests/test_release_packaging.py",
)

_MUTATION_SNIPPET_CHECK = (
    "import pathlib, sys;"
    "from agency_runtime.core.evals.decision_conformance import MUTATIONS;"
    "bad=[m.mutation_id for m in MUTATIONS"
    " if pathlib.Path(m.source_path).read_text(encoding='utf-8').count(m.before)!=1];"
    "print('mutation snippets checked:', len(MUTATIONS), '| stale:', bad);"
    "sys.exit(1 if bad else 0)"
)


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]
    slow: bool = False


def _pytest(*files: str) -> tuple[str, ...]:
    # No --basetemp. The hosted job points it at an owner-private directory
    # outside the checkout; pointing it inside the working tree instead makes
    # the file-trust, host-boundary and turn-boundary suites fail en masse
    # (205 false failures, measured). pytest's default system-temp basetemp is
    # what a plain local run already uses, and that run is green.
    return (
        sys.executable,
        "-m",
        "pytest",
        *files,
        "-q",
        "-W",
        "error",
        "-p",
        "no:cacheprovider",
    )


def gates() -> tuple[Gate, ...]:
    return (
        Gate(
            "ruff check",
            (sys.executable, "-m", "ruff", "check", "agency_runtime", "tests", "scripts"),
        ),
        Gate(
            "ruff format --check",
            (
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "agency_runtime",
                "tests",
                "scripts",
            ),
        ),
        Gate("dependency consistency", (sys.executable, "-m", "pip", "check")),
        Gate("committed whitespace", ("git", "diff", "--check", "HEAD", "--")),
        Gate("tracked release inputs", (sys.executable, "scripts/verify_release_hygiene.py")),
        Gate("documentation metadata", (sys.executable, "scripts/docs_metadata.py", "--check")),
        Gate(
            "policy availability",
            (sys.executable, "scripts/update_policy_availability.py", "--check"),
        ),
        Gate("worklog ledger", (sys.executable, "scripts/update_worklog.py", "--check")),
        Gate("documentation contracts", (sys.executable, "scripts/verify_docs.py")),
        Gate(
            "workflow contracts",
            _pytest(*WORKFLOW_CONTRACTS),
        ),
        Gate("mutation snippets", (sys.executable, "-c", _MUTATION_SNIPPET_CHECK)),
        Gate(
            "fast production spine",
            _pytest(*PRODUCTION_SPINE),
            slow=True,
        ),
        Gate(
            "AR-119 matrix evidence",
            _pytest(*MATRIX_EVIDENCE),
            slow=True,
        ),
        Gate(
            "dashboard UI",
            (
                "node",
                "--test",
                "--experimental-test-coverage",
                "--test-coverage-include=agency_runtime/dashboard/**/*.js",
                "--test-coverage-lines=95",
                "--test-coverage-branches=86",
                "--test-coverage-functions=93",
                "tests/dashboard_ui.test.mjs",
            ),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="skip the two long test suites")
    parser.add_argument("--list", action="store_true", help="list the gates and exit")
    arguments = parser.parse_args()

    selected = [gate for gate in gates() if not (arguments.fast and gate.slow)]
    if arguments.list:
        for gate in selected:
            print(f"{gate.name:26} {' '.join(gate.command)}")
        return 0

    started = time.perf_counter()
    for index, gate in enumerate(selected, 1):
        if gate.command[0] == "node" and shutil.which("node") is None:
            print(f"[{index}/{len(selected)}] {gate.name}: SKIPPED (node is not installed)")
            continue
        print(f"[{index}/{len(selected)}] {gate.name} ...", flush=True)
        gate_started = time.perf_counter()
        completed = subprocess.run(gate.command, cwd=REPOSITORY, check=False)
        elapsed = time.perf_counter() - gate_started
        if completed.returncode != 0:
            print(f"\nFAILED: {gate.name} (exit {completed.returncode}, {elapsed:.1f}s)")
            print("Nothing after this gate ran. Fix it and run again.")
            return 1
        print(f"    ok ({elapsed:.1f}s)")

    total = time.perf_counter() - started
    print(f"\nAll {len(selected)} gates passed in {total / 60:.1f} min.")
    print(
        "Not covered here: Linux-only behaviour, the decision-conformance mutation "
        "phase, and the integration coverage shards. Run `gh workflow run ci.yml` "
        "when a change could be platform-sensitive."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
