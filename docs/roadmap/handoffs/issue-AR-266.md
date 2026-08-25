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
branch: codex/ar266-local-retrieval-smoke
evidence_commit: 2bea0c763243757895032d8552da988368a64ecb
minimum_ledger_commit: 9adee235d74d0302e1afe090e26064a24d66d471
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320
---

# AR-266 active recovery capsule

## checkpoint

- Worktree `/tmp/agency-runtime-ar266-retrieval.nVONyD` is on branch
  `codex/ar266-local-retrieval-smoke`, based on exact fetched `origin/main`
  `4d2f88895f8fb8e3234ff4d8dbef47108c830476`.
- Current clean implementation/ledger head is `9adee235`; substantive commits
  `382fb4d9` and `2bea0c76` integrate the current host runtime and add bounded
  embedding dimensions, with ledger commits `04cef50f` and `9adee235`.
- Store schema is 48, integrity is `ok`, and the enabled roster has 278 workers.
  The pre-mutation SQLite online backup also passed integrity check.
- Effective Agency config SHA-256 after the atomic retrieval-only update is
  `2261184786cfb0911b4a8eeb429f3011edb2ed28b20b4da3f6ca14de43e52468`.
- Both gateways are active. Current launcher-manifest SHA-256 values are
  `ace4ad8d3014216ff176018353e8ea7909377c82998c34892c8241a78b707b64`
  for OpenClaw and
  `75f44200e7b052e33f2b691e8337a6172970174785bb8fb3edad57057c7dbfe6`
  for Hermes.

## completed-evidence

- AR-286 regression-first implementation passes 167 focused tests with
  warnings as errors. Ruff check/format, documentation gates, and independent
  review are green; no Critical, High, or Medium finding remains.
- Agency's local embedding adapter returned exactly 1,024 dimensions from
  `qwen3-embedding:latest`. The local structured adapter returned a complete,
  schema-valid reranking from `qwen3-14b-abliterated:latest`.
- Four forced host-labelled AR-266 smokes (`codex`, `claude`, `hermes`,
  `openclaw`) each applied both local provider stages and recovered 16 novel
  candidates. Codex and Claude were evaluator-only; their native config,
  OAuth, and canary evidence were untouched.
- OpenClaw's fresh native Store trace
  `4fbd059b-ea18-4ce7-8332-0446a70fdb9f` contains accepted workforce routing,
  the exact parent alias/profile, and an applied local embedding attempt. The
  native response carried a real Agency header and loaded `code-reviewer`.
- OpenClaw remains on audited `2026.7.1-2`, its primary remains
  `litellm/task-general`, and its native model/provider document is
  semantically unchanged. Hermes remains on `0.20.4`; its native config hash
  stayed byte-identical through the Agency refresh.
- Failed evidence is preserved: OpenClaw's implicit missing-`main` invocation
  was rejected before allocation; Hermes honored SIGTERM but its process
  returned exit 1 during stop; an earlier isolated test launcher correctly
  refused before allocation when its explicit embedding-stub URL was absent.

## current-state

The local Agency-only config is validated and active in `shadow` mode. Explicit
global capability routes use free local Ollama models and do not replace the
OpenClaw/Hermes host defaults. Both installed host projections come from this
same checkout and accept the new dimensions field. The forced four-host path
passes; OpenClaw native parent integration passes through Store-backed routing.
Hermes native retrieval proof is the next bounded live step.

## unresolved-gates

- Complete the fresh native Hermes retrieval turn and exact Store correlation.
- Run the remaining proportionate gates and record final before/after Store and
  host evidence. The complete warning-strict corpus and hosted workflow remain
  intentionally undispatched.
- Keep the full AR-266 shadow-value acceptance box open: this bounded smoke is
  real provider evidence, not the complete safety/quality matrix and not an
  additive-production recommendation.
- Resolve the inherited `test_configuration.py` default-mode expectation
  separately from AR-266; fetched main declares `strict`, while that test still
  expects `fast`.
- Keep tracker #320 open while the live shadow-value gate remains unresolved.

## exact-blocker

There is no external blocker. The only current incomplete live step is the
fresh Hermes bridge turn. OpenClaw's non-delivered CLI run remains active in
Store and must not be promoted into outbound-delivery or terminal-finalization
proof.

## next-bounded-work-package

1. Create this local recovery/ledger pair, then run one fresh Hermes native
   turn without changing Hermes config.
2. Correlate the Hermes Store trace and retain any failure without unchanged
   retry.
3. Run proportionate repository gates, update this capsule and both issue
   records with final evidence, and create the final local recovery/ledger pair.

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
