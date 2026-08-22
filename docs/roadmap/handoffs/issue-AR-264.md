---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-22
tags: [handoff, contractors, hiring, prompts, workforce]
related:
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-265-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-266-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-267-create-nested-config-parents-privately.md
  - docs/roadmap/issue-AR-268-accept-null-openclaw-control-errors.md
  - docs/roadmap/issue-AR-269-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/issue-AR-270-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-271-preserve-openclaw-model-receipt-fields.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 4d2a75ab19b1844f28ad7e27cd2462f93dfc5ec9
minimum_ledger_commit: 00b6b24bf04a8bb6d76f82a766a9d7fe2c03e027
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Clean pair `d9a1a7ce` / `1a737ef8` contains the prompt-build-order repair; `f76050d7` remains an ancestor.
- Agency-only install `1eeba99b-49a1-4db5-b561-9d985c30d29e` completed with bundle `d6b7acf4...`, launcher `391a5759...`, runtime `5b67d882...`, and 15/15 contractors. OpenClaw itself was not reinstalled; Agency config stayed byte-identical and only OpenClaw timestamp metadata changed.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general`. Agency is loaded with ten hooks; Telegram/Slack are connected and probe-green. Hermes and all proven hosts remain untouched.
- Fresh exact-status trace `bf21e9a8...`, Store run `c571cf9b...`, routing `e2a41ef8...`, and finalization `dec9e3fb...` delivered the exact five-line header. Deterministic abstention proves control activation/final delivery, not LiteLLM workforce inference.
- Changed `loop-library` request trace `2c4e81be...` hit the 80.744-second OpenClaw hook budget before native reply generation. Store run `eeb31163...` remains `active`/`in_progress`; no failure receipt, skill row, or success is claimed. The free 30B target is contract-capable but too slow for this native path.
- Only `task-agency-router` now targets installed free `ollama/qwen3-14b-abliterated`, with reasoning level `none`; all 102 unrelated deployment identity hashes and the 103 deployment count are unchanged. A zero-credential diagnostic trace `6a761259...` made no call and is not a model verdict.
- Credential-correct 14B trace `2317d975...` accepted all three stages in 37.768 seconds, exact OpenClaw profile/provider/alias, and no provider fallback. Fresh native `tmux` trace `79abdac7...` completed Store run `6b7651b6...`, routing `1908650f...`, binding `rmb-19107899...`, specialist `5f11b004...`, skill row `b54c5916...`, and finalization `64a97d43...`; the exact five-line header records inference and no delegation.
- Store schema remains 47; pre-install online backup integrity is `ok` and SHA is `11e0ddc4...`. Fresh post-live backup remains pending. Actual backing-model identity remains unavailable because LiteLLM reports the alias only.
- Exact substantive trace `35efa94c...` accepted all Agency stages and recorded two specialists plus `openclaw-operations`, but native `task-general` omitted `agency_finalize`; Store run `e2e9e65d...` closed `response_invalid` and no Telegram reply is claimed. AR-277's first-pass-only guidance repair is focused-green but not installed.

## completed-evidence

- Agency-only install, OpenClaw activation, exact-status finalization, native `healthcheck` evidence, and harness-scoped LiteLLM alias selection are proven.
- Exact substantive Agency-only acceptance is proven with the free 30B target; exact-status native header/finalization now pass with the installed prompt-order repair.
- Native skill acceptance now passes; exact substantive native acceptance remains open. No hosted workflow, push, PR, tracker mutation, host canary, protected-host change, or matrix movement occurred.

## exact-blocker

1. Checkpoint AR-277 without its rejected second-pass candidate.
2. Install Agency only into stopped OpenClaw and run a genuinely changed substantive work unit.
3. Require exact first-pass header/Store/provider correlation; preserve failures and keep Hermes untouched.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Commit the first-pass-only repair and ledger row.
2. Reinstall Agency into OpenClaw only and run the changed native proof.
3. Take the post-live online Store backup and run proportionate final gates.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_roster_inference_adapter.py tests/test_inference_profiles.py -q -W error
python -m pytest tests/test_installer_registration.py -q -W error
python -m pytest tests/test_config_policy_namespace_runtime.py tests/test_openclaw_streaming_policy.py -q -W error
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Preserve all credential values and failed receipts; record only names, presence, hashes, and redacted sources.
- Do not run unsupported OpenClaw/Hermes child canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
