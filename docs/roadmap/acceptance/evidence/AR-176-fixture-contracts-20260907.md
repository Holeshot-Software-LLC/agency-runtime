---
title: "AR-176 current fixture-contract reconciliation evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, testing, security, isolation]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md
  - docs/worklog/2026-07-27-b520fa7-full-gate-contracts.md
supersedes: []
superseded_by: null
---

# AR-176 current fixture-contract reconciliation evidence

## Observable outcome and scope

The six stale cases carried by AR-127/130/131 and one old cleanup fixture now
exercise current contracts without restoring removed behavior. The repair changes four test files,
not Python runtime, coverage thresholds, exclusions, skips or provider policy.
Main before repair is 891f0c3273220c9c8f1c9b8649582aea3c492018; owned branch
starts from its exact merge ledger d09ba163cf245a4608eed34081049e46a36169e0.

The July implementation b520fa765ffdef93ad499a088f79d247ce910e75 and its dated
11-case/670-case/full-corpus history remain separate from these fresh runs.
A historical success is not a new aggregate coverage or live-host result.

## Contract decisions checked against source

- Removed public agency.delegate returns unknown-tool and cannot fabricate
  execution. Two identical real-shaped native observer events record one
  execution without inventing a specialist identity.
- The first invalid Stop response is terminal response_invalid, not a
  corrective decision:block. Exact replay remains idempotent; changed text
  stays terminal; neither host records continue or retry_exhausted.
- The synthetic POSIX directory chain supplies absent-ACL evidence at the
  extracted helper's actual Store boundary. Real ACL-denial tests remain.
- File read permission 0644 is allowed inside a separately private directory.
  Group/other write, foreign ownership, links and invalid identity stay denied.
- Failed inference selects no fallback staff and opens no implicit turn.
  Operator-owned prompt text survives both calls. Current inference-first
  policy has no forced coordinator dependencies, so neither historical
  fallback coordinator is installed into this operator-only legacy roster.

The initial repaired run reached an additional obsolete assertion in the same
public-route case: it expected those retired fallback dependencies to be
seeded. Existing no-match tests and NO_MATCH_FALLBACK_SLUGS=() confirm the
intended current behavior. That assertion is corrected, not skipped; its
intermediate failure is preserved below.

## Six original current failures

Command on the unchanged test files:
```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_turn_scoped_evidence.py::test_public_delegate_and_post_tool_hook_record_one_execution tests/test_turn_scoped_evidence.py::test_stop_retry_terminally_stops_both_native_hosts_without_loop tests/test_storage_parent_trust.py::test_posix_parent_trust_requires_private_or_sticky_protected_chain tests/test_storage_parent_trust.py::test_storage_file_trust_requires_owner_mode_identity_and_single_link tests/test_public_api.py::test_public_route_repairs_legacy_fallback_roster_without_opening_turns -q -W error
```

Captured stdout (file-URI schemes, if any, are removed for repository docs;
assertions and failure content are not changed):
```text
FFFFFF                                                                   [100%]
=================================== FAILURES ===================================
_________ test_public_delegate_and_post_tool_hook_record_one_execution _________

tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_public_delegate_and_post_0')

    def test_public_delegate_and_post_tool_hook_record_one_execution(tmp_path: Path) -> None:
        store = Store(tmp_path / "agency.db")
        run_preflight(
            store,
            session_id="session",
            trace_id="turn",
            user_message="Review authentication and report the result.",
            host="codex",
        )
        arguments = {
            "agent": "reviewer",
            "task": "Review authentication",
            "backend": "spawn_agent",
            "trace_id": "turn",
            "session_id": "session",
            "work_unit_id": "unit-auth",
            "worker_kind": "generic-worker",
            "worker_id": "worker-1",
            "native_run_id": "native-run-1",
        }
    
        observed = handle_tool_call("agency.delegate", arguments, store=store)
>       assert observed["status"] == "delegation observed"
               ^^^^^^^^^^^^^^^^^^
E       KeyError: 'status'

tests/test_turn_scoped_evidence.py:318: KeyError
___ test_stop_retry_terminally_stops_both_native_hosts_without_loop[claude] ____

host = 'claude'
tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_stop_retry_terminally_sto0')

    @pytest.mark.parametrize("host", ["claude", "codex"])
    def test_stop_retry_terminally_stops_both_native_hosts_without_loop(
        host: str,
        tmp_path: Path,
    ) -> None:
        store = Store(tmp_path / "agency.db")
        store.create_run(
            trace_id="turn",
            session_id="session",
            host=host,
            metadata={"request_kind": "nontrivial"},
        )
        store.record_specialist_loaded("session", "reviewer", trace_id="turn")
        bridge = HookBridge(host, store=store)
        payload = {
            "hook_event_name": "Stop",
            "session_id": "session",
            "turn_id": "turn",
            "last_assistant_message": "Missing header.",
        }
    
        # Codex may omit stop_hook_active. The durable prior continue action is the
        # retry authority for both native hosts.
        first = bridge.handle(payload)
        terminal = bridge.handle(payload)
        exact_replay = bridge.handle(payload)
    
        # A corrective Stop uses the documented decision:block continuation shape.
>       assert first["decision"] == "block"
               ^^^^^^^^^^^^^^^^^
E       KeyError: 'decision'

tests/test_turn_scoped_evidence.py:403: KeyError
____ test_stop_retry_terminally_stops_both_native_hosts_without_loop[codex] ____

host = 'codex'
tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_stop_retry_terminally_sto1')

    @pytest.mark.parametrize("host", ["claude", "codex"])
    def test_stop_retry_terminally_stops_both_native_hosts_without_loop(
        host: str,
        tmp_path: Path,
    ) -> None:
        store = Store(tmp_path / "agency.db")
        store.create_run(
            trace_id="turn",
            session_id="session",
            host=host,
            metadata={"request_kind": "nontrivial"},
        )
        store.record_specialist_loaded("session", "reviewer", trace_id="turn")
        bridge = HookBridge(host, store=store)
        payload = {
            "hook_event_name": "Stop",
            "session_id": "session",
            "turn_id": "turn",
            "last_assistant_message": "Missing header.",
        }
    
        # Codex may omit stop_hook_active. The durable prior continue action is the
        # retry authority for both native hosts.
        first = bridge.handle(payload)
        terminal = bridge.handle(payload)
        exact_replay = bridge.handle(payload)
    
        # A corrective Stop uses the documented decision:block continuation shape.
>       assert first["decision"] == "block"
               ^^^^^^^^^^^^^^^^^
E       KeyError: 'decision'

tests/test_turn_scoped_evidence.py:403: KeyError
______ test_posix_parent_trust_requires_private_or_sticky_protected_chain ______

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71b1c74dd4f0>
tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_posix_parent_trust_requir0')
os_facade = <class 'tests.conftest._OSFacade'>

    def test_posix_parent_trust_requires_private_or_sticky_protected_chain(
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        os_facade,
    ) -> None:
        parent = tmp_path / "private"
        chain = store_security._directory_chain(parent)
        metadata = {candidate: _directory_metadata(mode=0o755) for candidate in chain}
        metadata[parent] = _directory_metadata(mode=0o700)
        monkeypatch.setattr(
            store_security,
            "os",
            os_facade(
                store_security.os,
                name="posix",
                missing=frozenset({"getxattr"}),
            ),
        )
        monkeypatch.setattr(store_security.os, "lstat", metadata.__getitem__)
    
>       assert store_security.storage_parent_is_trusted(
            parent,
            is_windows=False,
            effective_uid=1001,
        )
E       AssertionError: assert False
E        +  where False = <function storage_parent_is_trusted at 0x71b1c8f6d1c0>(PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_posix_parent_trust_requir0/private'), is_windows=False, effective_uid=1001)
E        +    where <function storage_parent_is_trusted at 0x71b1c8f6d1c0> = store_security.storage_parent_is_trusted

tests/test_storage_parent_trust.py:164: AssertionError
_____ test_storage_file_trust_requires_owner_mode_identity_and_single_link _____

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71b1c74dd7c0>
tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_storage_file_trust_requir0')

    def test_storage_file_trust_requires_owner_mode_identity_and_single_link(
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        metadata = SimpleNamespace(
            st_mode=stat.S_IFREG | 0o644,
            st_uid=1001,
            st_dev=1,
            st_ino=2,
            st_nlink=1,
            st_file_attributes=0,
        )
        monkeypatch.setattr(store_security.os, "lstat", lambda _path: metadata)
        monkeypatch.setattr(
            store_security.os,
            "geteuid",
            lambda: int(metadata.st_uid),
            raising=False,
        )
>       assert not store_security.storage_file_is_trusted(tmp_path, is_windows=False)
E       AssertionError: assert not True
E        +  where True = <function storage_file_is_trusted at 0x71b1c8f6d4e0>(PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_storage_file_trust_requir0'), is_windows=False)
E        +    where <function storage_file_is_trusted at 0x71b1c8f6d4e0> = store_security.storage_file_is_trusted

tests/test_storage_parent_trust.py:352: AssertionError
____ test_public_route_repairs_legacy_fallback_roster_without_opening_turns ____

tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1954/test_public_route_repairs_lega0')

    def test_public_route_repairs_legacy_fallback_roster_without_opening_turns(
        tmp_path: Path,
    ) -> None:
        runtime = AgencyRuntime(str(tmp_path / "agency.db"))
        runtime.store._activate_prevalidated_agent(
            {
                "slug": "operator-specialist",
                "name": "Operator Specialist",
                "source": "operator",
                "version": "1.0.0",
                "description": "A legacy operator-owned specialist.",
                "prompt_body": "Preserve this prompt.",
            }
        )
    
        for trace_id in ("diagnostic-route-1", "diagnostic-route-2"):
            receipt = runtime.attest_native_host(
                "hermes",
                session_id="legacy-session",
                trace_id=trace_id,
            )
            routing = runtime.route(
                "legacy-session",
                "ok",
                trace_id=trace_id,
                host="hermes",
                capability_receipt=receipt,
            )
            assert routing["selected_ids"] == []
>           assert routing["fallback_companion_ids"] == [
                "agents-orchestrator",
                "chief-of-staff",
            ]
E           AssertionError: assert [] == ['agents-orch...ief-of-staff']
E             
E             Right contains 2 more items, first extra item: 'agents-orchestrator'
E             Use -v to get more diff

tests/test_public_api.py:370: AssertionError
=========================== short test summary info ============================
FAILED tests/test_turn_scoped_evidence.py::test_public_delegate_and_post_tool_hook_record_one_execution
FAILED tests/test_turn_scoped_evidence.py::test_stop_retry_terminally_stops_both_native_hosts_without_loop[claude]
FAILED tests/test_turn_scoped_evidence.py::test_stop_retry_terminally_stops_both_native_hosts_without_loop[codex]
FAILED tests/test_storage_parent_trust.py::test_posix_parent_trust_requires_private_or_sticky_protected_chain
FAILED tests/test_storage_parent_trust.py::test_storage_file_trust_requires_owner_mode_identity_and_single_link
FAILED tests/test_public_api.py::test_public_route_repairs_legacy_fallback_roster_without_opening_turns
6 failed in 3.66s

```

## Intermediate repair result

```text
.....F                                                                   [100%]
=================================== FAILURES ===================================
____ test_public_route_repairs_legacy_fallback_roster_without_opening_turns ____

tmp_path = PosixPath('/tmp/pytest-of-holeshot/pytest-1955/test_public_route_repairs_lega0')

    def test_public_route_repairs_legacy_fallback_roster_without_opening_turns(
        tmp_path: Path,
    ) -> None:
        runtime = AgencyRuntime(str(tmp_path / "agency.db"))
        runtime.store._activate_prevalidated_agent(
            {
                "slug": "operator-specialist",
                "name": "Operator Specialist",
                "source": "operator",
                "version": "1.0.0",
                "description": "A legacy operator-owned specialist.",
                "prompt_body": "Preserve this prompt.",
            }
        )
    
        for trace_id in ("diagnostic-route-1", "diagnostic-route-2"):
            receipt = runtime.attest_native_host(
                "hermes",
                session_id="legacy-session",
                trace_id=trace_id,
            )
            routing = runtime.route(
                "legacy-session",
                "ok",
                trace_id=trace_id,
                host="hermes",
                capability_receipt=receipt,
            )
            assert routing["selected_ids"] == []
            assert routing["status"] == "inference_unavailable"
            assert routing["fallback_companion_ids"] == []
            assert routing["fallback_applied"] is False
            assert "decision_id" not in routing
            assert runtime.store.get_run(trace_id) is None
    
        assert runtime.store.get_open_traces_for_session("legacy-session") == []
        assert runtime.store.get_specialist_prompt("operator-specialist")["prompt_body"] == (
            "Preserve this prompt."
        )
        for slug in ("agents-orchestrator", "chief-of-staff"):
>           assert runtime.store.get_roster_entry(slug)["source"] == SOURCE_REPOSITORY
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E           TypeError: 'NoneType' object is not subscriptable

tests/test_public_api.py:381: TypeError
=========================== short test summary info ============================
FAILED tests/test_public_api.py::test_public_route_repairs_legacy_fallback_roster_without_opening_turns
1 failed, 5 passed in 2.29s

```

## Focused current contracts

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_turn_scoped_evidence.py::test_removed_public_delegate_cannot_fabricate_native_execution tests/test_turn_scoped_evidence.py::test_stop_rejects_first_invalid_response_without_a_correction_loop tests/test_storage_parent_trust.py::test_posix_parent_trust_requires_private_or_sticky_protected_chain tests/test_storage_parent_trust.py::test_storage_file_trust_requires_owner_mode_identity_and_single_link tests/test_public_api.py::test_public_route_preserves_operator_roster_without_inference_fallbacks_or_turns -q -W error
```

```text
......                                                                   [100%]
6 passed in 2.30s
```

No native harness run is represented by these synthetic tests. Actual native
headers and injection checks are recorded separately in
[the live audit](AR-404-live-header-audit-20260907.md).

## Combined-package cleanup fixture

The first current 14-module package was not green: 466 passed, one failed,
one existing skip and 64 Windows-named deselections in 77.40s. Its one failure
is test_installer_residual_fail_closed_branches. Fresh untouched-main
reproduction at 891f0c32 confirms this is not introduced by the first repair.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_coverage_final_delegation_private.py::test_installer_residual_fail_closed_branches -q -W error --tb=short
```

The unchanged-main run reports one failed in 0.18s. The injected replace error
is OSError("replace failed"), but a list.append cleanup double leaves its
staging tree behind. atomic_install_tree therefore raises AtomicInstallTreeError:
atomic install recovery is incomplete. That retained-path detection is correct.

The repaired double invokes the actual guarded remove_private_directory,
then records the call. It asserts both stage and target absent. The isolated
case passes (0.16s). No cleanup guard or production error is relaxed.

## Seven-case fresh verification

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_turn_scoped_evidence.py::test_removed_public_delegate_cannot_fabricate_native_execution tests/test_turn_scoped_evidence.py::test_stop_rejects_first_invalid_response_without_a_correction_loop tests/test_storage_parent_trust.py::test_posix_parent_trust_requires_private_or_sticky_protected_chain tests/test_storage_parent_trust.py::test_storage_file_trust_requires_owner_mode_identity_and_single_link tests/test_public_api.py::test_public_route_preserves_operator_roster_without_inference_fallbacks_or_turns tests/test_coverage_final_delegation_private.py::test_installer_residual_fail_closed_branches -q -W error
```

```text
.......                                                                  [100%]
7 passed in 7.26s
```

## Combined current order-sensitive package

The following 14 modules include every test module changed by July's b520fa7,
its Node diagnostic and today's four changed modules with current completion,
response and inference-first neighbors. This is one process in the listed
order, not the historical 670-count package or a new full corpus.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_turn_scoped_evidence.py tests/test_storage_parent_trust.py tests/test_public_api.py tests/test_completion_policy_boundary.py tests/test_response_contract.py tests/test_no_match_fallback.py tests/test_adapter_parity.py tests/test_coverage_final_delegation_private.py tests/test_dashboard_service_coverage_complete_operations.py tests/test_doctor.py tests/test_executable_namespace_security.py tests/test_owned_process_core_hardening.py tests/test_roster_authority_gap_coverage_ar91.py tests/test_roster_sync_gap_coverage_child.py -q -W error -k 'not windows'
```

Captured final stdout:
```text
................... [ 30%]
........................................................................ [ 46%]
........................................................................ [ 61%]
........................................................................ [ 76%]
........................................................................ [ 92%]
....................................                                     [100%]
467 passed, 1 skipped, 64 deselected in 135.49s (0:02:15)
```

## Current named production spine

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_storage_file_trust.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_upstream_selection_eval.py tests/test_decision_conformance.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_owner_authority.py tests/test_security_turn_boundaries.py tests/test_canary_coverage_complete.py tests/test_complexity_refactors.py tests/test_coverage_final_host_cli.py tests/test_resident_manager_lifecycle.py -q -W error
```

Captured final stdout:
```text
... [ 99%]
........                                                                 [100%]
1085 passed, 3 skipped in 111.62s (0:01:51)
```

The three skips are existing. The spine and neighboring package overlapped a
real native Hermes battery; these wall times are not staffing benchmarks.

## Current UI and coverage floors

```bash
set -o pipefail
node --test --experimental-test-coverage '--test-coverage-include=agency_runtime/dashboard/**/*.js' --test-coverage-lines=95 --test-coverage-branches=86 --test-coverage-functions=93 tests/dashboard_ui.test.mjs | tail -28
```

Captured output tail:
```text
  type: 'test'
  ...
1..220
# tests 224
# suites 0
# pass 224
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 409.378053
# start of coverage report
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# file                   | line % | branch % | funcs % | uncovered lines
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# agency_runtime         |        |          |         |
#  dashboard             |        |          |         |
#   app.js               |  95.45 |    87.96 |   71.70 | 431 467-469 483-490 515-520 524-525 530-536
#   charts.js            | 100.00 |   100.00 |  100.00 |
#   dashboard-actions.js |  94.53 |    47.10 |  100.00 | 128-129 132-133 149 159-160 176-177 211-214 243 252-253 276 311 319-320 348 389-390 393-394 429 473
#   dashboard-config.js  |  99.28 |    96.69 |  100.00 | 230-231 291-292
#   dashboard-core.js    |  99.05 |    92.98 |  100.00 | 345-346 449 482-483
#   dashboard-live.js    |  95.34 |    87.38 |   98.77 | 63-64 242-244 276-277 360-363 372-373 676 750-751 798-831 852-854 863 875 903-904 938 1229-1230 1237-1238 1354-1355 1362 1441-1442 1627-1628 1767-1769 1784-1787 1796-1799 1893 1924-1925 1938-1940 1964-1966 1969-1970 2044-2045 2047-2048 2059-2060 2214 2247 2355-2363 2377-2381 2389-2390 2399-2400 2430-2431
#   dashboard-render.js  |  97.96 |    86.25 |   97.01 | 120-128 777-782 896-897 933-935 1458 1461-1462 1494-1495 1654-1655 1923-1928 2323-2340
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# all files              |  96.93 |    86.78 |   95.74 |
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# end of coverage report
```

## Historical implementation evidence

The exact July eleven-node list was not durably retained in the cited worklog;
do not invent a reconstructed list and label it original. Its faithful record
reports 11 passed in 1.53s after the repair, then a 670-pass/one-skip neighboring
package. The dated production review subsequently records 8,021 passes,
61 skips and one expected failure in 32:11. Those facts remain historical.

Today's combined module package covers all affected July modules and the
current seven repairs. ADR-0105 removes the mandatory fresh exhaustive gate;
ADR-0224 retains failed diagnostic history and the 97-percent optional floor.
No aggregate coverage, six-interpreter, Windows-native or all-harness success
is inferred from this test-only change.

## Focused Node diagnostics

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_smoke_coverage_complete.py -q -W error
```

```text
36 passed in 2.97s
```

This module retains non-runnable Node and invalid-script rejection; the
14-module package includes missing-Node static validation. smoke.py preserves
the distinct FileNotFoundError/OSError branches and immediate argv revalidation.

## Strict record and lint checks

Commands:
```bash
set -e
export PYTHONPATH=.
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_policy_availability.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_worklog.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py --require-tracker
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_tracker.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime tests scripts
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime tests scripts
git diff --check
```

Captured output:
```text
checked 1217 Markdown documents
worklog index is current (2039 commits)
documentation validation passed for 1217 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```

A subsequent complete Ruff lint/format and diff check also passes after the
receipt append: All checks passed; 766 files already formatted. No automatic
CI success is inferred from these local checks.
