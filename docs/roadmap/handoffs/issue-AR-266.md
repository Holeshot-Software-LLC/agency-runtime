---
title: "AR-266 active recovery capsule"
status: active
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [handoff, workforce, embeddings, retrieval, inference]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-266
branch: codex/ar266-dense-hybrid-workforce-recall
evidence_commit: fc0770392b5a2cc38c589d2411698d0a0ac602ae
minimum_ledger_commit: fc0770392b5a2cc38c589d2411698d0a0ac602ae
hard_checkpoint_percent: 50
tracker_url: null
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
- No tracker, push, pull request, provider call, installation, or live canary is
  authorized by this handoff. The attempted stale-hook refresh failed because
  the installed config contains unsupported top-level fields.

## completed-evidence

- The implementation adds explicit embedding/reranker route resolution,
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
  provider call, installation, tracker mutation, push, or PR occurred.

## current-state

The local candidate is implementation-complete and verified in the isolated
worktree. It supports explicitly configured embedding and recall-reranker
models, safe current-turn subject queries, shadow/additive modes, complete
roster search, and bounded typed fallback. The implementation and its exact
ledger row are the next clean checkpoint; additive production value remains
unproven until a configured shadow evaluation uses a real provider.

## unresolved-gates

- Commit the verified implementation and exact worklog/roadmap ledger rows.
- Run a predeclared live shadow evaluation against explicitly configured
  embedding and reranker models before recommending additive production use.
- Resolve the inherited `test_configuration.py` default-mode expectation
  separately from AR-266; fetched main declares `strict`, while that test still
  expects `fast`.
- Repair the unsupported installed config before any host refresh or canary.
- Obtain explicit authorization before tracker creation, push, or PR work.

## exact-blocker

There is no local implementation blocker. Production-quality lift is not yet
proven because no live embedding/reranker shadow evaluation was authorized or
run. The installed hook refresh remains blocked by unsupported top-level config
fields, and tracker, push, PR, installation, and live-canary actions remain
authorization boundaries.

## next-bounded-work-package

1. Create the local implementation commit, then record it and the final handoff
   checkpoint in exact worklog/roadmap ledger rows.
2. After explicit authorization, configure a learned embedding model and a
   bounded text reranker, then run the predeclared shadow matrix without
   enabling additive production behavior.
3. Create/link the tracker and publish a PR only after separate outward-action
   authorization.

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
