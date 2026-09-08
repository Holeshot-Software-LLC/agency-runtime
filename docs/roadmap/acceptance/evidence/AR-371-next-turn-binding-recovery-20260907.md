---
title: "AR-371 next-turn resident binding recovery source evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, resident-managers, lifecycle, fail-open]
related:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
  - docs/roadmap/handoffs/issue-AR-371.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-371 next-turn resident binding recovery source evidence

## Source finding and scope

At base `9b15107a`, `_commit_current_binding` rejects any pending trace other
than the incoming trace. Planning keeps returning that pending delivery mode;
ready commit returns binding_conflict and fail-open bookkeeping rolls back its
savepoint. No subsequent turn can own the pending delivery until the exact old
Stop happens. AR-371 step 1 keeps the delivered steward visible but does not
bound that state-machine stall.

`fail_preflight_attempt` closes a run before its host Stop. Therefore simply
clearing any pending claim whose run is closed would steal an active same-turn
delivery and manufacture availability. The candidate does not do that.

## Closed next-turn transition

Only the ready/fail-open writer, already inside BEGIN IMMEDIATE, can retarget:

1. The old pending trace and incoming trace are distinct exact recorded runs
   within the binding's same session/canonical host.
2. Old status is explicitly recognized, with a bounded valid aware ended_at.
   Allowed statuses are abandoned, canary_failed, completed, delegation_declined,
   preflight_failed, preflight_skipped, response_invalid, retry_exhausted,
   specialist_disabled and verification_failed. Unknown vocabulary is refused.
3. Incoming positive durable turn_sequence exceeds the old one and no newer
   same-host/session run exists. Incoming is active/in_progress without ended_at,
   or just closed preflight_failed with empty preflight state and valid ended_at.
4. Existing binding ID, kernel, control epoch and generation validation precede
   the existing full-state CAS. It retargets pending/last trace, keeps pending
   mode/generation and requires the new trace's own acknowledgment.

Plan/read/same-trace recovery does not mutate. Existing late Stop checks remain
exact-trace bound. A restore event newer than the claimed generation stays
outstanding after acknowledgment. Missing/retired run evidence is not reclaimed.
No schema, staffing policy, runtime defaults, native contract or authority change.

## Written, unrun regressions

`tests/test_resident_binding_recovery.py` adds 32 real-Store cases: ready and
fail-open recovery; read-only same-turn waiting; active old claim blocking while
the new fail-open close lands; ten recognized terminal statuses; unknown/missing/
malformed old proof; both old/new session and host scope; four invalid incoming
claim states; strictly forward/latest ordering; stale claim CAS and late Stop;
preserved extra restore generation; old control epoch and stale kernel boundaries.

The existing fail-open hook lifecycle regression is adapted for intentional
closed-old recovery and retains delayed old Stop/new Stop assertions. The step 1
header test's assertion is unchanged; only its obsolete pinned-claim comment is
updated. No test has been executed under the owner's code-first instruction.

## Static verification

Executed only lint/format and diff checks, using the existing private tool env:

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format agency_runtime/core/store/resident_binding.py tests/test_resident_binding_recovery.py tests/test_fail_open_binding_lifecycle.py tests/test_resident_manager_header_honesty.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime/core/store/resident_binding.py tests/test_resident_binding_recovery.py tests/test_fail_open_binding_lifecycle.py tests/test_resident_manager_header_honesty.py
git diff --check
```

First formatting changed two files and left two unchanged. Final formatting
left all four unchanged; lint reported All checks passed!, diff check exited 0.
No pytest, CI dispatch, model/provider request, native operation or owner Store
mutation ran. Independent frozen-source review and all execution evidence remain
pending; this is builder evidence, not isolated acceptance.
