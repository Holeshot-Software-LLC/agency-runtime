---
title: "AR-398 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-398-a-gap-turn-that-outruns-its-lease-leaves-no-receipt.md
  - docs/decisions/0214-close-a-preflight-attempt-on-its-token-not-its-lease.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-398
candidate_commit: 2ae2b9c2a212f96dddff593b0c6319259611e4c4
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/670
---

# AR-398 acceptance verification record

Frozen at the commit that added the doctor check (ADR-0214, approach items 1,
2 and 4). The close is guarded by the attempt token alone and names an expired
lease on the receipt; the hiring loop stops inside the lease and marks the
units it skipped; the receipt projector carries hiring codes one at a time.
Criterion 4 (`agency doctor` reports stuck runs) landed on the same branch as
`db_preflight_stuck`.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the close UPDATE requires the run to be active, in progress and held by the attempt token, no longer an unexpired lease; an expired lease becomes the receipt's invariant unless a stronger one is set` | 2026-09-05 | `agency_runtime/core/store/preflight.py:2225-2272` |
| 1 | file | `the invariant vocabulary gains preflight_lease_expired_before_close` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:30` |
| 1 | file | `the schema version is 49` | 2026-09-05 | `agency_runtime/core/store/schema.py:44` |
| 1 | file | `the receipt table's invariant CHECK admits the new code` | 2026-09-05 | `agency_runtime/core/store/schema.py:977-979` |
| 1 | file | `a pre-49 store is rebuilt in place with its rows copied and its triggers recreated` | 2026-09-05 | `agency_runtime/core/store/schema.py:5049-5088` |
| 1 | test | `test_a_close_after_the_lease_expired_still_writes_the_receipt asserts the run ends preflight_failed and the receipt carries the expiry invariant` | 2026-09-05 | `tests/test_gap_hiring_lease_budget.py:104-124` |
| 1 | test | `test_a_store_built_before_schema_49_is_rebuilt_to_accept_the_new_invariant rebuilds a legacy table, keeps its row and accepts the new invariant` | 2026-09-05 | `tests/test_gap_hiring_lease_budget.py:196-271` |
| 1 | command-output | `the loss measured before the change (613 s, expired lease, no receipt, run left in_progress) and copies e, f, g and h all closing inside the lease with a receipt` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-398-evidence-20260905.txt:4-35` |
| 2 | file | `the loop starts another round only when the time left fits the longer of one provider deadline and the longest measured round plus the margin, and stops with lease_budget_exhausted otherwise` | 2026-09-05 | `agency_runtime/core/selector/pipeline.py:1851-1871` |
| 2 | file | `the floor and the fit rule` | 2026-09-05 | `agency_runtime/core/selector/pipeline.py:1789-1814` |
| 2 | file | `units left unproposed carry hiring_lease_budget_exhausted on their event` | 2026-09-05 | `agency_runtime/core/selector/pipeline.py:1775-1777` |
| 2 | file | `run_preflight takes the lease instant before the attempt starts` | 2026-09-05 | `agency_runtime/core/preflight.py:1484-1488` |
| 2 | file | `the built route request is rebound with the lease instant` | 2026-09-05 | `agency_runtime/core/preflight.py:1581` |
| 2 | file | `_with_hiring_deadline replaces the field on a selector request and passes any other request shape through` | 2026-09-05 | `agency_runtime/core/preflight.py:879-888` |
| 2 | test | `a spent lease proposes nothing and every event says why; a lease with room lets every round run; the longest measured round raises the bar` | 2026-09-05 | `tests/test_gap_hiring_lease_budget.py:364-400` |
| 2 | command-output | `copy h: the turn closed at 390 s inside the lease, the sixth unit not_attempted with hiring_lease_budget_exhausted, the receipt carrying it` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-398-evidence-20260905.txt:33-47` |
| 3 | file | `each hiring code is normalised on its own and one that cannot be carried becomes hiring_reason_code_invalid, so the account never collapses to nothing` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:383-412` |
| 3 | test | `a colon code no longer silences the account; an uncarriable code is named; clean codes project as before` | 2026-09-05 | `tests/test_gap_hiring_lease_budget.py:442-478` |
| 3 | command-output | `copy g: six events in, an empty account out, on the pre-fix projector; copy h: the same shape yields seven hiring codes including one hire per hired unit` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-398-evidence-20260905.txt:22-53` |
| 4 | file | `a read-only query returns the runs at status active and preflight_state in_progress whose lease has passed, ordered by start` | 2026-09-05 | `agency_runtime/core/doctor.py:357-385` |
| 4 | file | `the db_preflight_stuck check warns per host with the oldest start when any attempt is stuck and passes when none is` | 2026-09-05 | `agency_runtime/core/doctor.py:388-415` |
| 4 | file | `the database block appends the check beside integrity, schema and roster` | 2026-09-05 | `agency_runtime/core/doctor.py:350-353` |
| 4 | test | `test_database_checks_report_attempts_stuck_past_their_lease expires two openclaw attempts beside a live hermes one and asserts the warn, the per-host count and the oldest start` | 2026-09-05 | `tests/test_doctor.py:394-424` |
| 4 | test | `test_database_checks_pass_when_no_attempt_is_stuck asserts the pass and the four database checks in order` | 2026-09-05 | `tests/test_doctor.py:427-449` |
| 4 | command-output | `the check against a copy of the live store names the eleven stuck attempts, ten openclaw and one hermes, matching a direct count` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-398-evidence-20260905.txt:59-78` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-398.1-20260905-a8c68a8e` | `659133eca68d2c5dd9327326529b23563353333b7591be84260704b05ee41498` | 2026-09-05 | preflight.py:2233-2272 closes on the attempt token alone (no lease in the UPDATE), clears preflight_state to a terminal status, and stamps preflight_lease_expired_before_close on the receipt; schema.py:977-979 admits the code; tests/test_gap_hiring_lease_budget.py:104-124 asserts both halves. |
| 2 | satisfied | `AR-398.2-20260905-55915700` | `50c03126a3acb9c954988da4f752cc54b606f16a4781e294c61c10d299e3d45e` | 2026-09-05 | pipeline.py:1863-1875 breaks the loop via _hiring_round_fits against the bound lease; 1775-1777 with _hiring_event marks unproposed units not_attempted with hiring_lease_budget_exhausted, projected by preflight_hiring_reason_codes; tests 364-407 and evidence copy h lines 33-47 confirm. |
| 3 | satisfied | `AR-398.3-20260905-f68e5db0` | `17543f1f84c3b93c272a595adb2d42bfb05f8f4653e06c8266e4c0c701ea18ae` | 2026-09-05 | AR-398-evidence-20260905.txt:22-53 records copy h, a PL/I six-unit gap replay on a fresh store copy at branch code, giving one hiring event per gap unit and a non-empty receipt hiring account, versus empty on pre-fix copy g; preflight_failure.py:383-415 and the three projector tests match. |
| 4 | satisfied | `AR-398.4-20260905-d1028121` | `23f7b8913198fa91239e03d94af6e7606021c0b1c151be18e5e0fe2d4f83b71d` | 2026-09-05 | doctor.py:357-415 adds db_preflight_stuck querying active runs with preflight_state in_progress past their lease, appended at 350-353 and reached by run_doctor at line 1074; tests/test_doctor.py:394-449 cover the warn and pass paths, and the evidence file records 11 such runs on a live-store copy. |

## Builder notes

Criterion 1 is stage-ready, not live-proven: every replay closed inside its
lease, so the expired-close path rests on the unit tests and on the pre-change
loss in copy b. Criteria 2 and 3 are live-proven on store copies g and h.
Criterion 2 was reworded before any verdict from a count to a per-unit code,
since receipt codes are de-duplicated. Criterion 3 originally asked for a hiring case per proposed hire; a fail-open
turn commits no pending hire by design (only a ready commit does), so the
criterion was reworded before any verdict to the hiring event each hire
leaves. Criterion 4 is met by `db_preflight_stuck`, which named eleven stuck
attempts on a copy of the live store.
