---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-22
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
  - docs/roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md
  - docs/roadmap/issue-AR-263-restore-codex-desktop-parent-hook-delivery.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
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
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/roadmap/AR-119-2919802e-accepted-outcome-proof.md
  - docs/roadmap/AR-119-f4f3d45e-hiring-risk-evidence.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 4d2a75ab19b1844f28ad7e27cd2462f93dfc5ec9
minimum_ledger_commit: 00b6b24bf04a8bb6d76f82a766a9d7fe2c03e027
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Clean branch pair `d9a1a7ce` / `1a737ef8` contains the prompt-build-order repair and ledger; fetched `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- Agency profile `linux-task-agency-router` remains harness-scoped to OpenClaw, using `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No protected-host route changed.
- Prompt-order Agency-only install `1eeba99b-49a1-4db5-b561-9d985c30d29e` completed with bundle `d6b7acf4...`, launcher SHA `391a5759...`, runtime digest `5b67d882...`, and 15/15 contractors. OpenClaw itself was not reinstalled; Agency config stayed byte-identical and only `/meta/lastTouchedAt` changed in OpenClaw.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general`, enabled/loaded with ten Agency hooks, and RPC-green. Telegram and Slack are running, connected, zero-reconnect, and probe-green. Hermes/LiteLLM stayed active; Hermes, Claude, ZCode, and Codex OAuth/model/canary were untouched.
- Fresh exact-status session `ar276-openclaw-nexus-status-promptorder-20260822-a`, trace `bf21e9a8-a9f0-442b-9d75-78dab94687d6`, Store run `c571cf9b-a990-4551-ba76-f0cb27e137ce`, routing `e2a41ef8-15cd-4242-8b6d-11a720227728`, and finalization `dec9e3fb-c8fc-4b14-a072-794171263f8b` completed. The exact five-line Agency header delivered `agency-steward`; deterministic abstention is control proof, not workforce-inference proof. Response/transcript SHAs are `b02a2f18...` / `e009951b...`.
- A changed same-session `loop-library` skill request was blocked after 80.744 seconds before native reply generation. Response SHA is `d8e84b4a...`; Store run `eeb31163-27d8-4091-986f-35d03a8e64b2` remains `active`/`in_progress` with no fabricated failure receipt. The free 30B target exceeded the native hook budget; this is a timeout, not successful staffing or a contract rejection.
- Only LiteLLM deployment `d594b69b-26f8-4bec-8531-e6c191ab6f6c` (`task-agency-router`) now targets installed free `ollama/qwen3-14b-abliterated`. All 102 unrelated deployment identity hashes remain `ca74e597...`, count remains 103, and target reasoning level `none` plus boolean settings were restored/preserved. OpenClaw native routing remains unchanged.
- First 14B CLI diagnostic `6a761259-b7e1-49fc-b4c9-ecaa18cd6da7` made zero calls because its process lacked the service-only credential. Artifact SHA `a6ee6023...` is retained as an operator-input failure and is not a model verdict. Actual answering model remains unavailable unless authoritative telemetry supplies it.
- Credential-correct 14B trace `2317d975-c960-4020-8755-f32308ffe94b` accepted planner, recruiter, and critic in 37.768 seconds through OpenClaw profile `linux-task-agency-router`, exact LiteLLM alias/model-group, and no provider fallback. Artifact SHA is `673c5ae7...`.
- Fresh native `tmux` session `ar276-openclaw-nexus-tmux-qwen14b-20260822-a`, trace `79abdac7-42f1-44e9-afad-bf5556df62aa`, Store run `6b7651b6...`, routing `1908650f...`, request binding `rmb-19107899...`, specialist `5f11b004...`, skill row `b54c5916...`, and finalization `64a97d43...` completed in 45.085 seconds. The exact five-line header records inference, `code-reviewer`, `tmux`, no delegation, and wrapper alias only. Response/transcript SHAs are `7f9a4674...` / `499187e8...`.
- Exact substantive session `ar276-openclaw-nexus-restart-qwen14b-20260822-a` accepted all Agency stages under trace `35efa94c...` with zero fallback, but native `task-general` omitted `agency_finalize` after read-only tools. Store run `e2e9e65d...` and finalization `7d5428e7...` are `response_invalid`; response/transcript SHAs `f4f6d7b7...` / `f0f9e359...` prove no valid header or Telegram delivery.
- AR-277 rejected the second-pass candidate, then installed the first-pass-only repair as Agency install `e834190a...`, bundle `521b1480...`, runtime `b5d546a6...`, launcher `41415e79...`. Changed trace `07e5ec33...` accepted all exact Agency LiteLLM stages with no fallback, but native `task-general` made 31 read-only tool calls and timed out at 240.461 seconds before `agency_finalize`; Store run `6726b5ce...` remains active/ready with no header or finalization claim.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 remains live-proven for native finalization and response delivery. Exact-status is deterministic control proof; the subsequent non-control turn now proves Agency harness/profile/alias selection and strict finalization.
- AR-273 now has fast accepted Agency-only and native skill routing through the exact LiteLLM profile/alias on free 14B; actual backing model telemetry remains unavailable.
- AR-274 expected-red is 2/2 exact failures; repair is 22 passed/1 skipped plus 453 passed/1 skipped, and fresh `healthcheck` header/Store proof now passes. Proportionate final gates remain; no exhaustive workflow was dispatched.
- AR-275 preserves bounded codes without model coupling. AR-276 prompt-build preflight and native skill proof pass. The exact substantive attempt is a retained AR-277 finalizer failure, so substantive native acceptance remains open.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Checkpoint the exact changed-work-unit timeout without promoting it to delivery.
2. Run one tighter fresh work unit that permits no host tool except `agency_finalize`.
3. Correlate first-pass header/Store/provider evidence, then take the post-live backup.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Commit the timeout checkpoint and ledger row.
2. Run the tighter changed native proof after an immediate telemetry check.
3. Take the post-live online Store backup and keep Hermes/proven hosts untouched.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

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

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Never expose credential values. Preserve hashes, environment-variable names, and populated booleans only.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change and no Codex canary belongs in this Linux package.
