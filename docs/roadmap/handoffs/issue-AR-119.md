---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, routing, workforce, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/worklog/2026-07-23-c1efcaf-instrumented-incident-recovery-and-corpus-variance.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
handoff_token: "AR-119:installed-clinical-instrumented:v1"
branch: codex/ar-115-live-routing-trust
evidence_commit: c1efcafed676bf6f7c1db6747fec38c0f5358589
minimum_ledger_commit: 1cc493b8001d6233ae283fed866825b5c5df07a2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

This is the bounded bootstrap projection for the next AR-119 package. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) remains the
complete historical and acceptance contract.

## Checkpoint

- Branch: codex/ar-115-live-routing-trust.
- Substantive evidence commit:
  c1efcafed676bf6f7c1db6747fec38c0f5358589.
- Minimum ledger commit:
  1cc493b8001d6233ae283fed866825b5c5df07a2.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The dispatch prompt supplies the exact current clean HEAD and source task ID.
  The HEAD may be newer than the minimum ledger commit but must contain it.

## Completed evidence

- An instrumented matched active-incident confirmation preserved the unchanged
  WorkforceInferenceOutcome before projection and passed with
  incident-responder, complete typed coverage, zero forbidden, ineligible, or
  conflict selections, and 8705.105 ms Agency latency.
- The instrumented process returned status 0 in 23.211480 seconds. Its
  report/stdout SHA-256 was
  2ba2801b64f965a107c85f63b881cbe74a673673202a1f5fd484b3ae034306fb;
  the complete Agency outcome SHA-256 was
  9afceec23eeecd8a4292dfc0731df2550fdeb1001bca647f5e04c0fed10cba25.
- The required unchanged 19-case corpus then passed 17/19 Agency arms with
  precision 0.910714, recall 0.879310, F1 0.894737, 17/19 typed coverage,
  p50 8143.807 ms, p95/max 13144.781 ms, and zero scored safety violations.
- The corpus process took 414.760604 seconds. Its stdout SHA-256 was
  f5b462bc32bcaa000cb6ee426312022a62a3058c7518f598d09afb720572184a;
  the exact projection SHA-256 was
  604279f7eedcaf59318c4fa69d75b01c6792ed8814e64a251f4d727745ca0a7c.
- No product, policy, parser, coverage, latency, or call-budget rule changed.

## Exact blocker

- The newest complete corpus safely abstained on
  installed-cross-platform-release and clinical-legal-boundary-review; their
  complete pre-projection outcomes have not yet been preserved and compared
  with accepted observations.
- Complete Agency corpora have varied from 19/19 to 18/19 and 17/19. Repeatable
  complete selection is not yet proven.
- No complete corpus has produced 19 benchmark-valid upstream arms. Malformed,
  no-response, or timed-out upstream arms remain validity failures, never
  comparative losses.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
instrumented matched confirmation limited to installed-cross-platform-release
and clinical-legal-boundary-review. Preserve each complete unchanged Agency
outcome outside the repository through the same pass-through router before
benchmark projection. Keep the audited snapshot, Windows/Codex context, full
tool union, provider, requested and actual model, 15000 ms gate, and one-call
fast budget unchanged.

The equivalent unchanged CLI selection is:

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --case installed-cross-platform-release --case clinical-legal-boundary-review --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Capture both streams before parsing. If both Agency arms pass, make no product
or policy change and run one further unchanged complete 19-case corpus. If
either fails, compare its captured plan, proposal ranks, confidence, margin,
and deterministic rejection with prior accepted observations; change only a
genuinely general governed semantic proven by that exact evidence.

## Verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50
~~~

## Constraints

- Acknowledge sole-writer ownership before editing or live evaluation.
- Preserve every accumulated AR-119 commit and the clean branch.
- Do not weaken typed coverage, add a scenario route, raise the 15000 ms gate,
  increase the one-call budget, or reinterpret malformed upstream output.
- Do not claim Agency is better.
- Do not push, open or update a PR, trigger hosted Actions, mutate or close
  issue #132, or mark AR-119 complete.
- Update the canonical issue and replace this capsule when the package changes;
  create the required substantive and ledger commits.
