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
  - docs/worklog/2026-07-23-ar119-installed-release-plan-shape-variance.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
handoff_token: "AR-119:installed-release-instrumented-confirmation:v1"
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

- One instrumented two-case matched run preserved both complete unchanged
  Agency outcomes before projection. It took 49.659155 seconds, returned status
  1, and produced identical 714,064-byte report/stdout documents with SHA-256
  4cafdb1280992ae775a71c250a424ab4c592d0994833ebec719b0b7e1d6f9989;
  stderr was empty.
- The benchmark was valid. Clinical/legal passed at 9068.9 ms with both helpful
  specialists and complete typed coverage. Installed release safely abstained
  at 13335.75 ms with required_agents_missing, no_safe_sufficient_team, and
  recruiter_abstained. Both retained one applied explicit-model call and zero
  forbidden, ineligible, or conflict selections.
- The installed and clinical/legal outcome hashes were respectively
  fd6ac7223283022a37e01b932a7da52b672a9850eb79cf90a756aba96a8514db
  and f3fd40b6342c668ba66cb601b26bf78132269bf93f8decd39acd0d878f0a4556.
  The exact projection hash was
  ee48658669d609e278f3e364444a7de77059d6ba9c78b035873e5d9078df667d.
- The installed first unit ranked cross-platform-installer-engineer first at
  1.0 but also required generation-preparation. All 15 executable candidates
  missed only that capability. Its only whole-roster owners are two ineligible
  design specialists. This is configured-model plan-shape variance and a
  correct fail-closed decision, not a proven governed defect.
- No product, policy, parser, worker-contract, coverage, latency, or call-budget
  rule changed.

## Exact blocker

- Clinical/legal recovered. Installed release has now repeated a safe
  abstention after many accepted observations; the preserved occurrence used an
  unsupported visual-generation capability in a software plan.
- Complete Agency corpora have varied from 19/19 to 18/19 and 17/19, so
  repeatable complete selection is not yet proven.
- No complete corpus has produced 19 benchmark-valid upstream arms. Malformed,
  no-response, or timed-out upstream arms remain validity failures, never
  comparative losses.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
further instrumented matched confirmation limited to
installed-cross-platform-release. Preserve the complete unchanged Agency
outcome outside the repository through the same pass-through router before
benchmark projection. Keep the audited snapshot, Windows/Codex context, full
tool union, provider, requested and actual model, 15000 ms gate, and one-call
fast budget unchanged.

The equivalent unchanged CLI selection is:

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --case installed-cross-platform-release --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Capture both streams before parsing. If Agency passes, make no product or
policy change and run one further unchanged complete 19-case corpus. If it
fails, compare its captured plan and deterministic rejection with the preserved
generation-preparation occurrence; change only a genuinely general governed
semantic proven by exact evidence. Repeated provider plan shape alone is not
permission to weaken controlled capability semantics.

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
