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
   The verified HMAC session tombstone barrier also rejects any retired sequence
   at or beyond the candidate. Tombstones do not retain host identity, so newer
   retirement in the same session conservatively blocks even for another host;
   other sessions and older retired turns do not block.
4. Existing binding ID, kernel, control epoch and generation validation precede
   the existing full-state CAS. It retargets pending/last trace, keeps pending
   mode/generation and requires the new trace's own acknowledgment.

Plan/read/same-trace recovery does not mutate. Existing late Stop checks remain
exact-trace bound. A restore event newer than the claimed generation stays
outstanding after acknowledgment. Missing/retired run evidence is not reclaimed.
No schema, staffing policy, runtime defaults, native contract or authority change.

## Regressions and bounded wrap-up execution

`tests/test_resident_binding_recovery.py` adds 36 real-Store cases: ready and
fail-open recovery; read-only same-turn waiting; active old claim blocking while
the new fail-open close lands; ten recognized terminal statuses; unknown/missing/
malformed old proof; both old/new session and host scope; four invalid incoming
claim states; strictly forward/latest ordering; stale claim CAS and late Stop;
preserved extra restore generation; old control epoch and stale kernel boundaries.
Four additional cases create real Store tombstones, retire those run rows and
exercise the real ready transaction: newer same-host retirement, newer other-host
same-session retirement, unrelated-session retirement and older retirement. This
is not a full trim-command exercise.

The existing fail-open hook lifecycle regression is adapted for intentional
closed-old recovery and retains delayed old Stop/new Stop assertions. The step 1
header test's assertion is unchanged; only its obsolete pinned-claim comment is
updated. The initial 32-case checkpoint was written but unrun under the owner's
code-first instruction. The owner then authorized tests for the clean stopping
point; this exact focused command passed on the final retention-aware source:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_resident_binding_recovery.py tests/test_fail_open_binding_lifecycle.py tests/test_resident_manager_header_honesty.py -q -W error
```

Raw completion output (exit 0):

```text
..........................................                           [100%]
46 passed in 11.90s
```

The first four progress dots arrived in the initial tool response; the completion
above contains the remaining dots. No failed test attempt preceded this result.

## Review and retention correction

Source checkpoint `c3b217f1`, ledger `5538beb6`, preserves the initial candidate.
Merge `4516e055` and ledger `0836dfd1` integrate published main through `1048a120`.
Parent's preliminary runtime review found no scoped issue. During the final
source trace, the builder identified a retention edge: a newer retired run was
absent from the live-only latest-turn query. The final correction reuses the
existing `Store._find_authoritative_trace_by_hash` HMAC/tombstone ordering barrier
without writing identity state or extending the schema.

Independent reviewer `/root/ar176_inventory` reviewed the final bounded delta
and reported no remaining scoped finding. This is source review, not that
reviewer's execution result; the 46-pass run above is builder evidence.

## Static verification

The original code-first checkpoint executed only lint/format and diff checks,
using the existing private tool environment:

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format agency_runtime/core/store/resident_binding.py tests/test_resident_binding_recovery.py tests/test_fail_open_binding_lifecycle.py tests/test_resident_manager_header_honesty.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime/core/store/resident_binding.py tests/test_resident_binding_recovery.py tests/test_fail_open_binding_lifecycle.py tests/test_resident_manager_header_honesty.py
git diff --check
```

First formatting changed two files and left two unchanged. Final formatting
left all four unchanged; lint reported All checks passed!, diff check exited 0.
The final retention correction reformatted its two changed files and again
passed scoped Ruff lint. No CI dispatch, model/provider request, native operation
or owner Store mutation ran. Broad suite, isolated acceptance and installed live
delivery remain separate pending gates; this is builder evidence, not isolated
acceptance or issue completion.
