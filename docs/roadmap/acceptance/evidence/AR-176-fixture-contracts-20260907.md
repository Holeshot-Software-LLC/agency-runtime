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

The six stale cases carried by AR-127/130/131 now exercise current contracts
without restoring removed behavior. This checkpoint changes three test files,
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
