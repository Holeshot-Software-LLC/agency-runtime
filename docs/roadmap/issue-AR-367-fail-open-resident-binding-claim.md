---
title: "AR-367: Fail-open turns never claim their resident binding; persistent hosts re-inject the kernel every turn"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [resident-managers, fail-open, rule8, persistent-host, bug]
related:
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/roadmap/issue-AR-354-host-cli-coverage-suite-failing-on-main.md
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-367
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/464
depends_on: []
blocks: []
---

# AR-367: Fail-open turns never claim their resident binding; persistent hosts re-inject the kernel every turn

## Problem

On the persistent host (claude) the resident-manager binding lifecycle —
inject the kernel once, acknowledge at Stop, reuse on later turns, restore
after compaction — was only ever claimed inside the preflight ready commit,
and the Stop path only acknowledged a binding it could read from a ready
recipe. A turn that fails open (`preflight_failed`, the AR-353 window)
delivers the kernel with its capsule but never writes a recipe, so the
planned binding is never claimed and never acknowledged.

Measured 2026-09-02 on this installation's live store (claude sessions
since 2026-09-01 20:00Z): six sessions with only fail-open turns had no
`resident_manager_bindings` row at all; the goal session itself had 12
turns, 11 of them fail-open, and one row stuck `pending` on an abandoned
ready turn since 22:11Z — every one of its later capsules carried
`delivery=injected` and the full kernel body. With roughly 60% of turns
failing open that day, the persistent host paid the whole kernel on most
turns and never entered the acknowledge/restore lifecycle.

Ten pre-existing failures in `tests/test_resident_manager_lifecycle.py`
(AR-354) trace to the same gap: their `ping` prompt now classifies as
substantive, fails open in the offline store, and leaves nothing for the
acknowledgement helper to read.

## Current state

Fixed in this change (see Implementation). Live proof follows the next
deploy: a fail-open claude turn must leave a `pending` binding bound to its
trace, the Stop pass-through must acknowledge it, and the following turn's
binding line must read `delivery=reused`.

## Approach

Treat a fail-open close exactly like a ready commit for the binding it
delivered:

- `Store.fail_preflight_attempt(..., resident_manager_binding=)` claims the
  planned binding in the same transaction that closes the run, under a
  savepoint (`claim_resident_manager_binding_on_failure`): a conflicting or
  invalid claim rolls back to the savepoint and the close still lands —
  bookkeeping never costs the turn (Rule 8).
- `run_preflight` threads the binding it planned into
  `_persist_preflight_failure`.
- `Store.get_completion_evidence_snapshot` projects the claimed binding for
  a fail-open run from the pending row bound to that trace
  (`_pending_resident_manager_binding_projection`, rebuilt from the row's
  control epoch — the binding id is a function of session, host, and
  epoch), so the existing Stop acknowledgement
  (`HookBridge._acknowledge_resident_manager_delivery`) covers fail-open
  turns without a second code path.

## Implementation (2026-09-02)

- `agency_runtime/core/store/resident_binding.py`:
  `_pending_resident_manager_binding_projection`,
  `pending_resident_manager_binding`, `claim_resident_manager_binding_on_failure`.
- `agency_runtime/core/store/preflight.py::fail_preflight_attempt` claims the
  binding after the failure receipt; `agency_runtime/core/preflight.py`
  initialises and threads `resident_binding`;
  `agency_runtime/core/store/sqlite.py::get_completion_evidence_snapshot`
  falls back to the pending row.
- Tests: `tests/test_fail_open_binding_lifecycle.py` — the claim on a
  fail-open close (row `pending`, bound to the trace), the snapshot
  projection and a successful acknowledgement, the Stop pass-through
  acknowledging and the next turn planning `reused` (kernel body absent,
  disclosure present), and a conflicting claim leaving the close intact.
  `tests/test_resident_manager_lifecycle.py` improves from 10 to 7 failures
  without any fixture change; the rest is AR-354's.

## Dependencies

- AR-356 (the fail-open capsule the binding rides in); AR-354 records the
  remaining lifecycle-suite failures.

## Acceptance

- [ ] A fail-open turn on a persistent host claims its planned binding with
      the close and the Stop pass-through acknowledges it; the next turn
      plans `reused` and omits the kernel body (regression tests).
- [ ] A conflicting or invalid claim never fails the fail-open close
      (regression test).
- [ ] Live: on this installation a fail-open claude turn leaves an
      acknowledged binding and the following capsule reads `delivery=reused`.
