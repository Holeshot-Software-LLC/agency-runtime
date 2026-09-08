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
evidence_commit: f670e6b564af75e4b6e5a1a576db4b719080efa6
minimum_ledger_commit: 2236d99635bc9a54963c41a7f8dd17a19df260b6
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/735
---

# AR-409 reserved staffing call recovery capsule

## Checkpoint

This is a branch-only implementation checkpoint, not an installed build.
The metadata SHAs identify the combined implementation/evidence and ledger;
the normal merge integrates AR-408's accepted `ae916dd1` checkpoint.
Worktree: `/tmp/agency-runtime-ar409-reserve-required-staffing`.
Tracker #735 and all filing reciprocals are present.
Source PR: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/739.
It deliberately leaves #735 open pending the required installed live checkpoint.

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
unchanged. Acceptance is frozen to combined committed candidate `f670e6b5`.
All five criteria have isolated satisfied judgments; installed owner-harness
live delivery evidence remains pending. Keep AR-409 in_progress and #735 open.
The first all-five verifier invocation produced no judgments: the exact Claude
package/bin directories were 0775 and the executable trust guard refused them.
Authorized exact `chmod g-w` restored 0755 and local usable status. Actor unknown;
no bytes/profiles/guards changed. The retry satisfied 1–4, then criterion 5 was
unavailable; both directories had returned to 0775 with 00:08:07/08Z mtimes.
The parent authorized one supported Codex-verifier attempt for only missing
criterion 5; it satisfied the same frozen candidate's excerpts. Preserve all
five judgments. No additional Claude repairs or guard changes occurred.

## Same-task continuity

Preserve the three reviewed runtime/test paths and their record paths.
AR-408 and main `f408b6f2` are integrated. Runtime bytes remain identical to
artifact source `51909ae8`. Never discard another worker's changes.
Telemetry reached 40.8% remaining at 2026-09-07T23:31:11Z. The filing has a clean
substantive/ledger pair; checkpoint this implementation before live work.

## Next bounded work package

1. Publish the accepted-source PR without closing #735 or marking done.
2. Run normal PR gates and merge, preserving the exact runtime identity.
3. Notify the parent immediately so owner installation/live checks can start.
4. Parent installs/live-checks that exact combined candidate under existing
   configured authority, then records PR/merge and native evidence honestly.

## Verification

Exact commands/results and failed intermediate attempts are in
docs/roadmap/acceptance/issue-AR-409.md. The final focused command is:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_staffing_call_reservations.py tests/test_preflight_provider_deadline.py tests/test_preflight_failure_diagnosis.py tests/test_transport_failure_causes.py tests/test_workforce_inference.py tests/test_decision_conformance.py -q -W error -k 'not windows'
```

No exhaustive workflow, coverage shard, compatibility matrix or staffing model
call was run. Two Claude passes produced four satisfied judgments; the first
pass and second pass's fifth criterion were locally unavailable. One supported
Codex-only missing-criterion invocation then satisfied criterion 5.

## Constraints

Keep default/owner budgets, providers, zero-signal trigger, shared deadline,
validation, critic and hiring policy. No deterministic picker, invented hints,
trust bypass, credential/profile mutation or historical receipt rewriting.
Conservative future cache/gap reservations can abstain sooner. Five calls do
not fund subject plus both repairs and critic; no paired live quality or
end-to-end latency-equivalence claim is supported. Builder records evidence;
the isolated verifier alone judges acceptance.
