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
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-266
branch: codex/ar266-local-retrieval-smoke
evidence_commit: 050245651ce958f3b1fdb51069c4fed73d193494
minimum_ledger_commit: 48e03933a90985697e0c5bd6d4e4e731d58189d3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320
---

# AR-266 active recovery capsule

## checkpoint

- Worktree `/tmp/agency-runtime-ar266-retrieval.nVONyD` is on branch
  `codex/ar266-local-retrieval-smoke`, based on exact fetched `origin/main`
  `4d2f88895f8fb8e3234ff4d8dbef47108c830476`.
- The clean code checkpoint is `05024565` with ledger `48e03933`. It follows
  schema-48 integration, bounded dimensions, complete hook budgets, and the
  Hermes-native finalizer. Run `git log -2 --oneline` after resume to verify the
  documentation checkpoint pair created after this capsule projection.
- Store schema is 48, integrity is `ok`, and the enabled roster has 278 workers.
  The pre-mutation SQLite online backup also passed integrity check.
- Effective Agency config SHA-256 after the atomic retrieval-only update is
  `2261184786cfb0911b4a8eeb429f3011edb2ed28b20b4da3f6ca14de43e52468`.
- Both gateways are active. Current launcher-manifest SHA-256 values are
  `ace4ad8d3014216ff176018353e8ea7909377c82998c34892c8241a78b707b64`
  for OpenClaw and
  `cd025c3589d9ca8f592ae1e24114fee9df2b8477420f80ac518ea9b993c59f93`
  for Hermes.

## completed-evidence

- AR-286/AR-287 provide exact 1,024-dimension embeddings and complete host-hook
  budgets. Four forced host-labelled smokes applied both local recall stages;
  Codex and Claude were evaluator-only, leaving native OAuth/config/canaries
  untouched.
- Native OpenClaw `2026.7.1-2` trace
  `8e6033b2-6ab6-4e1d-ac3b-dca792e8eb2d` applied exact-alias parent inference,
  local embedding, and local reranking, then wrote a real Agency header with
  `gis-analyst` and `codebase-onboarding-engineer`. Its native primary remained
  `litellm/task-general`; no config changed. The CLI-only run remains active
  with no `message_sent` or finalization row, so it is retrieval/header proof,
  not terminal or Telegram-delivery proof. Historical failures remain in the
  canonical issue; the unsupported embeddings-stub claim is retracted.
- AR-288 exposes Hermes-native `agency_finalize` without native config changes;
  three red-before regressions, 109 focused tests, the 856-test spine, and local
  gates pass. System Python lacks `pytest`, so the 160-snippet substitute passed.
- Agency alone was reinstalled into Hermes from this checkout. Hermes `0.20.4`
  reports the `agency-runtime` native toolset; installed runtime digest is
  `824c4d2b267c3d5c56610c44284ec1242113f900d4177ca5d193c0e907b59702`.
  Its native config remains byte-identical at SHA-256
  `95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d`.
- Fresh Hermes session `20260825_112803_2eae8e`, trace
  `20260825_112803_2eae8e:fbbb0bcf-ef22-40de-bbd4-030fb5919eb9:cb12755e`,
  completed run `3fa51d15-99f2-49d1-bd22-3713ca7cc6c8`. Request-scoped binding
  `rmb-49d1637099543d6f77e47dbb8be8c243` is validated in preflight; no persistent
  Hermes binding-table row is expected.
- The same turn applied LiteLLM profile `linux-task-agency-router` with exact
  requested alias/model group `task-agency-router`, local Ollama embedding
  `qwen3-embedding:latest`, and local Ollama reranker
  `qwen3-14b-abliterated:latest`. One recruiter attempt was rejected before its
  bounded repair succeeded; there was no alternate-provider fallback. Hermes's
  answering receipt remained native `task-general`.
- Routing decision `29759202-cbc1-458b-a366-5835fcdce3d0` loaded `gis-analyst`
  and `codebase-onboarding-engineer`; specialist-load rows are
  `80521db4-c461-4668-b4df-e7fe1b29a656` and
  `e6d27363-07ee-42ca-93c2-7385babf7b3b`. No skill or child was requested.
  Terminal finalization `e87cec42-c0db-4252-8e92-5c64c556980f` committed exact
  response hash `91c4a26d30097a6bf18e55dfb792d7c6e1532fe6ba61bca723596b847470daa4`.
- The final post-smoke SQLite online backup has integrity `ok`, schema 48, roster 278,
  and SHA-256
  `a57b7dc0a965fd1bf54c30a2a190ba86712a2aed52c87b80080f371c3d1f6628`.
  The preinstall backup also had integrity `ok`, schema 48, and roster 278.
- Distinct failures remain preserved. Session `20260825_111718_f91ab5` applied
  both recall stages but correctly rejected an oversized `host_transport`
  draft. Session `20260825_112213_7fef69` applied both stages but failed closed
  after two unsafe recruiter classifications (`staff_without_safe_team`).
  Neither input was retried unchanged.

## current-state

The local Agency-only config is validated and active in `shadow` mode. Explicit
global capability routes use free local Ollama models and do not replace native
host defaults. Forced four-host retrieval, native OpenClaw parent integration,
and native Hermes parent/embedding/reranker/finalizer correlation pass. Both
gateways are active. AR-288 is locally complete; AR-266 remains open only for
the full shadow-value matrix and does not recommend additive activation.

## unresolved-gates

- Create AR-288's tracker only after explicit authorization; no outward tracker
  write was made.
- Complete AR-266's full shadow-value safety/quality matrix. The complete
  warning-strict corpus and hosted workflow remain intentionally undispatched.
- Keep the full AR-266 shadow-value acceptance box open: this bounded smoke is
  real provider evidence, not the complete safety/quality matrix and not an
  additive-production recommendation.
- Resolve the inherited `test_configuration.py` default-mode expectation
  separately from AR-266; fetched main declares `strict`, while that test still
  expects `fast`.
- Keep tracker #320 open while the live shadow-value gate remains unresolved.

## exact-blocker

There is no Hermes runtime blocker. The unsupported embeddings-stub claim is
retracted: no repository path or retained artifact requires one, and live
retrieval used Agency's explicit Ollama profiles. AR-288 tracker creation needs
owner authorization. OpenClaw trace `8e6033b2-...` remains active in Store and
must not be promoted into terminal or outbound-delivery proof.

## next-bounded-work-package

1. Verify this worktree is clean and the latest substantive/ledger pair is at
   `HEAD`; do not resume from the shared checkout.
2. Reconcile the already-completed forced four-host retrieval smokes into the
   requested final evidence bundles without invoking Codex OAuth or canaries.
3. Continue only the remaining AR-266 full shadow-value matrix or an explicitly
   authorized host proof; do not rerun the retained Hermes inputs unchanged.

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
- Do not invent or require an embedding-stub launcher variable; no retained
  evidence identifies one, and live endpoints belong to Agency profiles.
- Preserve malformed/timed-out provider evidence as unavailable, not as an
  upstream loss or proof that baseline recall failed.
- Do not raise embedding safety bounds or slice/pad provider vectors; rejected,
  stripped, or mismatched dimension requests retain typed-only behavior.
