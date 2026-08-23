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
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
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
evidence_commit: a8022a92ed303c6dbd41fdfa2a0f652239070a99
minimum_ledger_commit: 4fab954b0224883439b978adccf95d515f753b3b
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
- Store schema remains 47. Post-live online backup integrity is `ok` and SHA is `47d868f5...`; all 15 packaged contractors remain exact-current. Actual backing-model identity remains unavailable because LiteLLM reports the alias only.
- Exact trace `35efa94c...` remains `response_invalid`, and changed trace `07e5ec33...` remains a native timeout. Tighter fresh trace `9bea1a3f...` applied all Agency stages with no fallback, called only `agency_finalize`, delivered the exact five-line header, and completed Store run `c24afc99...` plus finalization `07759321...` in 46.635 seconds.
- User-initiated Telegram trace `9ac12abc...` accepted deterministic status finalization `63140215...`, but native `task-general` emitted `NO_REPLY`; the first AR-278 failure remains retained.
- Clean pair `1ca46cc9` / `320dc7cf` installed the prompt repair as Agency-only install `74b4c0bc...`. Fresh trace `2eaaf8e9...` then accepted all three exact Agency LiteLLM receipts with no cross-provider fallback, selected two specialists, recorded `openclaw-operations`, and returned exact finalizer text. The text hash `202f0d58...` was prematurely terminal, so the canonical full-payload gate failed closed and Telegram queued no reply.
- Clean pair `a8022a92` / `4fab954b` defers only OpenClaw terminal commit to the audited full-payload gate and permits one exact, session-bound, expiring native reset acknowledgement. Agency-only install `87b518e8...` completed with bundle `7f94acf0...`, runtime `1816b6ad...`, launcher `c34c66be...`, 15 contractors, and no installer restart. Native restart is RPC/probe-green with 11 hooks and zero diagnostics. OpenClaw remains on `litellm/task-general` plus six original fallbacks; Agency config, Hermes, and all proven hosts remain untouched.
- Third Telegram trace `4552b87d...` proves exact harness/profile/alias routing, accepted decision `bbf1d404...`, and `code-reviewer` load, then ends `response_invalid` because native `task-general` emits exact `NO_REPLY` after accepted finalizer event `f9138f55...`. Terminal `9599d181...` and transcript/trajectory SHAs `81b54934...` / `38f1e716...` are retained; no Telegram outbound exists.
- Reset expected-red exit 227 now passes through `before_reset` with an exact bounded race wait; all 218 affected OpenClaw tests pass. The candidate is not installed.
- OpenClaw 2026.7.1-2 has no supported tool return-direct or post-model replacement surface. Its public finalizer hook cannot supply a reply, its dispatcher drops exact `NO_REPLY` before Agency's payload hook, and the public plugin SDK cannot register terminal tool presentation.

## completed-evidence

- Agency-only install, OpenClaw activation, exact-status finalization, native `healthcheck` evidence, and harness-scoped LiteLLM alias selection are proven.
- Exact substantive Agency-only acceptance is proven with the free 30B target; exact-status native header/finalization now pass with the installed prompt-order repair.
- Native skill and changed substantive CLI acceptance pass; Telegram channel acceptance remains blocked by AR-278's full-envelope conflict. No hosted workflow, push, PR, tracker mutation, host canary, protected-host change, or matrix movement occurred.

## exact-blocker

1. Agency inference/finalizer construction passes, but OpenClaw suppresses the model's post-tool `NO_REPLY` before the host-owned payload gate.
2. A supported OpenClaw return-direct/terminal-presentation or post-model replacement seam is required; direct send, rewrite, retry, or native config change is forbidden.
3. Preserve all failures and keep Hermes untouched.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Commit the reset regression/fix and exact blocker evidence.
2. Obtain or authorize the missing OpenClaw delivery capability before another live attempt.
3. Reinstall Agency and use new inputs only after that prerequisite; leave Hermes untouched.

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
