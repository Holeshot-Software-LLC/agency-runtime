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
candidate_commit: pending
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-398 acceptance verification record

Pending draft carried by the implementation branch (ADR-0214, approach items 1
and 2). The close is guarded by the attempt token alone and names an expired
lease on the receipt; the hiring loop stops inside the lease and marks the
units it skipped; the receipt projector carries hiring codes one at a time.
Criterion 4 (`agency doctor` reports stuck runs) is not implemented and is
recorded absent.

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
| 4 | absent | `none` | 2026-09-05 | `none` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

## Builder notes

Criterion 1 is stage-ready, not live-proven: every replay closed inside its
lease, so the expired-close path rests on the unit tests and on the pre-change
loss in copy b. Criteria 2 and 3 are live-proven on store copies g and h.
Criterion 2 was reworded before any verdict from a count to a per-unit code,
since receipt codes are de-duplicated. Criterion 3 originally asked for a hiring case per proposed hire; a fail-open
turn commits no pending hire by design (only a ready commit does), so the
criterion was reworded before any verdict to the hiring event each hire
leaves. Criterion 4 is open: `agency doctor` does not yet count runs left
`in_progress` past their lease.
