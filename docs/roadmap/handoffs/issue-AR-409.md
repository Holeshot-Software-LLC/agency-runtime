---
title: "AR-409 reserved staffing call recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, workforce, budgets, reliability]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/roadmap/acceptance/issue-AR-409.md
  - docs/decisions/0235-reserve-required-staffing-calls-before-optional-work.md
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-409
branch: codex/ar409-reserve-required-staffing
evidence_commit: 9946461a96007eda1ca06830121c4a29edeb2ea7
minimum_ledger_commit: 967ff2e806752fc1d4191ed332b7b326f25e81e3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/735
---

# AR-409 reserved staffing call recovery capsule

## Checkpoint

This is a branch-only implementation checkpoint, not an installed build.
The two metadata SHAs identify the reviewed implementation/ledger prerequisite;
the containing normal merge integrates AR-408's accepted `ae916dd1` checkpoint.
Worktree: `/tmp/agency-runtime-ar409-reserve-required-staffing`.
Tracker #735 and all filing reciprocals are present.

The reviewed code reserves required downstream calls and caps subject inference
at one actual call. Its final receipt refinement appends only the exact budget
cause when otherwise lost. The worker owns these scoped source/record commits;
the parent owns final PR/merge and installed delivery. No provider requests ran.

## Completed evidence

- New fixed-response flow: subject1/planner1/recruiter2/critic1 succeeds within
  strict five; subject plus both repairs requires six and refuses the doomed
  repair under five. No-subject default repair controls remain unchanged.
- Refunded pre-request failures may use a fallback; actual subject requests
  across the entire provider chain never exceed one.
- Exact stage caches remain usable before their own admission checks; the
  strict critic is fresh. Valid subject propagation and critic veto/repair
  behavior are covered without model calls.
- Real Store tests retain budget causes for zero-call and recruiter-reservation
  failure; existing status/verifier causes remain and duplicates are prevented.
- Pre-receipt-refinement broad suite: 532 passed, 1 skipped, 3 Windows deselected
  in 26.47s. Final related suite: 201 passed in 2.99s.
- Independent review: no remaining findings after receipt recheck; final
  independent subset 62 passed in 0.38s.
- Full 188-mutation run passed before receipt refinement. Fresh five-mutation
  subset (four new anchors plus fixture-support/default-budget control) killed
  all five after refinement. Routing, Ruff, format and diff checks passed.
- Initial nonprivate-umask conformance setup and four-only fixture-copy runs
  failed before mutations; exact attempts are preserved in the evidence draft.
- Combined AR-408/409: 210 focused passes in 3.89s; named production spine
  1085 passes/3 skips in 69.50s; fresh five mutation kills and routing passed.

## Exact blocker

AR-408 is integrated. Its historical five-call current-flow test now exercises
the isolated exhausted-critic boundary; the accepted original snapshot is
unchanged. Freeze acceptance to the combined committed candidate next.
Final combined acceptance verdicts and live delivery evidence remain pending.

## Same-task continuity

Preserve the three reviewed runtime/test paths and their record paths.
Normal-merge the exact published AR-408 checkpoint; if dirty, use a recoverable
stash scoped only to owned files. Never discard another worker's changes.
Integrate both AR-408 failure/timeout corrections and AR-409 reservations.
Telemetry reached 40.8% remaining at 2026-09-07T23:31:11Z. The filing has a clean
substantive/ledger pair; checkpoint this implementation before live work.

## Next bounded work package

1. Commit the combined source/evidence and immediate ledger.
2. Audit bounded excerpts and freeze acceptance to that combined candidate.
3. Run isolated single-criterion verification for all five criteria.
4. Parent installs/live-checks that exact combined candidate under existing
   configured authority, then records PR/merge and native evidence honestly.

## Verification

Exact commands/results and failed intermediate attempts are in
docs/roadmap/acceptance/issue-AR-409.md. The final focused command is:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_preflight_provider_deadline.py tests/test_preflight_failure_diagnosis.py tests/test_transport_failure_causes.py tests/test_workforce_inference.py tests/test_decision_conformance.py -q -W error -k 'not windows'
```

No exhaustive workflow, coverage shard, compatibility matrix, new live model
call or acceptance-verifier call was run in this worker package.

## Constraints

Keep default/owner budgets, providers, zero-signal trigger, shared deadline,
validation, critic and hiring policy. No deterministic picker, invented hints,
trust bypass, credential/profile mutation or historical receipt rewriting.
Conservative future cache/gap reservations can abstain sooner. Five calls do
not fund subject plus both repairs and critic; no paired live quality or
end-to-end latency-equivalence claim is supported. Builder records evidence;
the isolated verifier alone judges acceptance.
