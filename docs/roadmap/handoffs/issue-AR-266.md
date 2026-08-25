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
evidence_commit: 3cb2da6cfd60a5debd5ef8ad47730922d52bbdb2
minimum_ledger_commit: dfcb005c2605101a3c03418c0a3c6aacc16a8c1a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/320
---

# AR-266 active recovery capsule

## checkpoint

- Worktree `/tmp/agency-runtime-ar266-retrieval.nVONyD` is on branch
  `codex/ar266-local-retrieval-smoke`, based on exact fetched `origin/main`
  `4d2f88895f8fb8e3234ff4d8dbef47108c830476`.
- The latest prior recovery pair ends at `dfcb005c`; substantive commits
  `382fb4d9`, `2bea0c76`, and `3cb2da6c` integrate the current host runtime, add
  bounded embedding dimensions, and bind host hook timeouts to the complete
  inference budget. Ledger commits are `04cef50f`, `9adee235`, `f9860466`, and
  `dfcb005c`.
- Store schema is 48, integrity is `ok`, and the enabled roster has 278 workers.
  The pre-mutation SQLite online backup also passed integrity check.
- Effective Agency config SHA-256 after the atomic retrieval-only update is
  `2261184786cfb0911b4a8eeb429f3011edb2ed28b20b4da3f6ca14de43e52468`.
- Both gateways are active. Current launcher-manifest SHA-256 values are
  `ace4ad8d3014216ff176018353e8ea7909377c82998c34892c8241a78b707b64`
  for OpenClaw and
  `006594b31d139f97bd706085fd2b50e7f306b7353ea1d5b35dd00da49ecd862b`
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
  was rejected before allocation, and Hermes honored SIGTERM but its process
  returned exit 1 during stop. A prior capsule revision also asserted an
  embedding-stub launcher refusal, but retained no command, variable name, test,
  or artifact; exhaustive repository/evidence search found no such dependency,
  and the recorded smokes used live Ollama. That unsupported assertion is not
  acceptance evidence or a production prerequisite.
- Hermes session `20260825_092554_bd5aef` failed before provider attempt because
  the fresh CLI shell lacked the credential indirection that is populated in
  the gateway. A distinct securely bound session, `20260825_092951_6ab6b9`,
  reached the installed bridge but timed out: the 80-second generated hook did
  not cover its 120-second harness profile, and finalization correctly blocked
  the unverified draft. AR-287 preserves both failures and repairs the shared
  bridge/Store-lease budget; 160 focused tests pass.
- Agency alone was reinstalled into Hermes from this checkout. The installed
  plugin records 595 seconds, its launcher runtime digest is
  `6b87ffe9e589c5acc09a0f4795e7265a6e360116bab364ea034cf86624bb2c21`,
  and Hermes's native config hash remained byte-identical.
- Fresh trace
  `20260825_100145_81c6d2:1ebe5369-b94a-4df6-8cc8-7ec6875e66f9:5dc384f7`
  crossed the old 80-second boundary, reached ready preflight, and recorded
  successful exact-alias workforce plus applied local embedding and reranker
  receipts. Its operator-only `--max-turns 8` cap then injected a synthetic
  no-tool summary before `agency.finalize`; the stale header was correctly
  rejected and that distinct failure is preserved.
- AR-288 exposes Hermes-native `agency_finalize` without native config changes;
  three red-before regressions, 109 focused tests, the 856-test spine, and local
  gates pass. System Python lacks `pytest`, so the 160-snippet substitute passed.

## current-state

The local Agency-only config is validated and active in `shadow` mode. Explicit
global capability routes use free local Ollama models and do not replace the
OpenClaw/Hermes host defaults. Hermes now runs the AR-287 repair from this
checkout; OpenClaw remains active and untouched as break-glass. Forced
four-host retrieval and OpenClaw native parent integration pass. Hermes has
current provider and timeout evidence but still needs one normally budgeted,
Store-backed response that finalizes successfully. AR-288 now owns the concrete
missing native `agency_finalize` tool exposed by that live checkpoint; its
repository repair is ready for an Agency-only reinstall.

## unresolved-gates

- Install AR-288's self-contained Hermes native finalizer tool, then complete
  one changed native retrieval turn with exact Store correlation; do not retry
  any of the three failed inputs unchanged.
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

There is no external blocker. The Hermes timeout is fixed and installed. The
latest turn's artificial eight-iteration cap—not a missing live embedding URL—
forced a no-tool summary before finalization. OpenClaw's non-delivered CLI run
remains active in Store and must not be promoted into outbound-delivery proof.

## next-bounded-work-package

1. Commit the validated AR-288 repository repair and its ledger row.
2. Reinstall Agency alone; run and correlate one genuinely changed Hermes request.
3. Run proportionate gates, record final evidence, and create the final local
   recovery/ledger pair before moving to any other host.

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
