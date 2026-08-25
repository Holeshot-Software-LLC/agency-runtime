---
title: "AR-266 active recovery capsule"
status: active
category: roadmap
created: 2026-08-24
updated: 2026-08-25
tags: [handoff, workforce, embeddings, retrieval, inference]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-266
branch: codex/ar266-merge-ledger
evidence_commit: 042b5ed974486b067aba886750210e97c029a2d2
minimum_ledger_commit: 299b1ec59337bcb61d6ee881d58d7a43d53c31d2
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320
---

# AR-266 active recovery capsule

## checkpoint

- The isolated worktree is on
  `codex/ar266-dense-hybrid-workforce-recall` from exact fetched
  `origin/main` commit `fc0770392b5a2cc38c589d2411698d0a0ac602ae`.
- The shared main checkout contains another worker's OpenClaw changes and must
  remain untouched.
- Bootstrap telemetry reported 29.9 percent remaining. Planning and ledger
  commits `9629cc8e` and `71edf5cc` form the clean starting checkpoint.
- AR-266 and ADR-0164 preserve the existing 24 typed candidates as a guaranteed
  lane while searching the complete roster through additive lexical and
  learned-dense recall. Inference remains the sole final selector.
- Tracker [#320](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320)
  exists with `epic:workforce`; the owner authorized publication, and
  [PR #321](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/321)
  passed every automatic check and merged to exact `origin/main` commit
  `042b5ed974486b067aba886750210e97c029a2d2` without override. Its reviewed
  second parent is exact ledgered branch head
  `299b1ec59337bcb61d6ee881d58d7a43d53c31d2`.
- This merge-record package runs from that exact main commit in a second
  isolated worktree on `codex/ar266-merge-ledger`. The shared main checkout and
  its other worker's OpenClaw changes remain untouched.
- No provider call, model installation, config mutation, or live canary
  occurred on this box. The official Ollama installer was only downloaded to a
  temporary folder and signature-verified before the owner redirected model
  smoke testing to another machine.

## completed-evidence

- Implementation commit `51c7a8ec` adds explicit embedding/reranker route resolution,
  positive-only projections, exact vector validation, lexical+dense RRF, a
  model-bound two-entry cache, and typed-only failure evidence.
- Additive integration recovers a specialist beyond the 24 typed cards and
  leaves inference plus the unchanged verifier as the only staffing authority.
- Shadow retrieval has an independent two-call budget and cannot consume
  planner, recruiter, repair, or critic capacity. Missing actual-model identity
  fails closed before cache population or reuse.
- 144 focused retrieval/inference tests, 77 configuration/profile tests, 68
  receipt tests, and 147 routing/selection/hiring tests with one skip pass.
- The named fast spine passes 806 tests with 20 skips; 134 dashboard tests,
  full Ruff checks, every routing-eval threshold, and 151/151 decision
  conformance mutations pass.
- Independent security re-review reports GO on both High repairs. No live
  provider call, model installation, config mutation, or live canary occurred.
- Verified checkpoint `fee0a116` and ledger commit `b5fe8cb9` complete the
  original implementation bookkeeping. Tracker #320 and PR #321 now provide
  the outward publication records.
- Direct tracker verification confirms issue #320 is open with the exact
  `[AR-266]` title, URL, and `epic:workforce` label. The repository-wide strict
  tracker gates remain red on pre-existing historical missing-issue and state
  mismatches outside AR-266; ordinary documentation validation passes all 739
  files.
- PR #321's hosted gates pass: the 13-minute quality job, CodeQL, dependency
  review, source/dependency audit, uninstrumented performance, Windows Python
  3.11/3.12/3.13 portability, Ubuntu and Windows unsigned-distribution smoke,
  artifact assembly, and the automatic-gate summary all completed green.

## current-state

Exact fetched `origin/main` commit `042b5ed9` contains the verified, ledgered
AR-266 implementation from PR #321. It supports explicitly configured
embedding and recall-reranker models, safe current-turn subject queries,
shadow/additive modes, complete roster search, and bounded typed fallback.
Additive production value remains unproven until a configured shadow
evaluation uses real providers on the owner's model-capable machine.
Local preparation found a provider-native 1,024-dimension projection is needed
to keep the complete-roster batch under the unchanged scalar bound. AR-286 owns
that configuration path; no vector slicing or bound increase is authorized.

## unresolved-gates

- Publish this exact-main merge record through the required docs-only PR.
- Run a predeclared live shadow evaluation against explicitly configured
  embedding and reranker models before recommending additive production use.
- Complete AR-286 so an exact requested dimension is sent, verified, and bound
  into catalog identity before the local shadow evaluation.
- Resolve the inherited `test_configuration.py` default-mode expectation
  separately from AR-266; fetched main declares `strict`, while that test still
  expects `fast`.
- Repair the unsupported installed config before any host refresh or canary.
- Keep tracker #320 open while the live shadow-value gate remains unresolved.

## exact-blocker

There is no implementation blocker; PR #321 is merged and all automatic checks
passed. Production-quality lift is not yet proven because no live
embedding/reranker shadow evaluation ran. The installed hook refresh on this
box remains blocked by unsupported top-level config fields; model configuration
and live evidence have moved to the owner's model-capable machine.

## next-bounded-work-package

1. Commit and publish this exact-main merge checkpoint with its reciprocal
   worklog ledger row through the required docs-only PR.
2. On the model-capable machine, start from the resulting exact `main`,
   complete AR-286, configure a learned embedding model with a provider-native
   bounded dimension and a bounded text reranker, then run the predeclared
   shadow matrix without enabling additive production behavior.
3. Keep AR-266 and tracker #320 in progress until the live acceptance evidence
   is durable; do not present the merge itself as additive-value proof.

## same-task-continuity

Continue this package in the current task through normal compaction. The 50
percent telemetry threshold requires clean checkpoints but does not require a
new task, handoff receiver, or pause. If an operator chooses another model,
resume from this branch only after verifying the exact worktree, branch,
status, latest substantive/ledger pair, and unresolved gates above.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused AR-266 tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Do not mutate, switch, clean, stage, or commit the shared checkout.
- Do not make dense scores a selector, eligibility filter, hiring signal, or
  execution-authority source.
- Do not embed or retain raw prior transcript, prompts, negative fields, raw
  queries, or vectors.
- Do not treat an absent embedding route as permission to use the default
  inference profile.
- Preserve malformed/timed-out provider evidence as unavailable, not as an
  upstream loss or proof that baseline recall failed.
- Do not raise embedding safety bounds or slice/pad provider vectors; rejected,
  stripped, or mismatched dimension requests retain typed-only behavior.
