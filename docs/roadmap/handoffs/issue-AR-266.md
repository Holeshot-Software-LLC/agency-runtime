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
- Bootstrap telemetry reported 29.9 percent remaining, so the planning record
  and its ledger row are the first required clean checkpoint.
- AR-266 and ADR-0164 preserve the existing 24 typed candidates as a guaranteed
  lane while searching the complete roster through additive lexical and
  learned-dense recall. Inference remains the sole final selector.
- No tracker, push, pull request, provider call, installation, or live canary is
  authorized by this handoff. The attempted stale-hook refresh failed because
  the installed config contains unsupported top-level fields.

## completed-evidence

- Active code inspection proves typed recall is capped at 24 candidates per
  unit and recruiter candidates must come from the resulting detail cards.
- The complete governed recruiter index contains the positive card fields
  needed for lexical and learned-dense retrieval.
- ADR-0083, ADR-0118, and ADR-0121 permit deterministic recall and validation
  but reserve substantive staffing selection for inference.
- Security review rejects the legacy `agent_embeddings` table because it lacks
  exact projection, roster, model, dimension, and normalization identity.
- Evaluation design requires 100-percent baseline retention, zero unsafe
  additions, zero stale-index reuse, and no increase in false gap or hiring
  signals before additive activation.

## current-state

Planning is in progress. Runtime implementation and tests have not yet been
committed. The intended first slice is an in-memory, explicitly configured,
shadow-default hybrid recall path with an injectable embedding provider. It
must not silently use the default text provider or persist raw query/vector
content.

## unresolved-gates

- Implement explicit embedding-route resolution, safe projection and query
  schemas, exact vector validation, reciprocal-rank fusion, and bounded cache.
- Integrate shadow/additive results before recruiter detail-card construction
  without changing baseline typed order or staffing verification.
- Add provider, inference, context, cache, dynamic-hiring, scaling, and
  evaluation tests; run focused and named fast gates.
- Repair the unsupported installed config before any host refresh or canary.
- Obtain explicit authorization before tracker creation, push, or PR work.

## exact-blocker

There is no local implementation blocker. The installed hook refresh is
separately blocked by unsupported top-level config fields, and tracker, push,
pull-request, installation, and live-canary actions remain authorization
boundaries. Neither condition blocks the isolated local implementation and
verification package.

## next-bounded-work-package

1. Commit this roadmap/ADR/handoff planning record and its exact worklog row.
2. Implement the positive-only hybrid recall module and explicit learned
   embedding provider/profile boundary in shadow-default mode.
3. Integrate additive candidates into workforce recruiter cards, record safe
   receipts, and prove typed-only fallback plus context-sensitive retrieval.
4. Run focused review and verification, then create a clean substantive and
   ledger checkpoint before reporting any outward-action boundary.

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
