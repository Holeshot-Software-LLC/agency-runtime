---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-24
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
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
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
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar278-openclaw-one-pass
evidence_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
minimum_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` is based on clean failure-evidence ledger checkpoint `01a8ad24`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected-host route changed.
- Earlier fresh session `130e58cd...` passed deterministic status/skill/Telegram, then exact restart-safety run `324dcb7c...`, trace `755985e5...`, routing `436eaef9...` selected two specialists and produced three exact-profile LiteLLM wrapper receipts with zero cross-provider fallback.
- Its native `task-general` parent made 30 model calls and 108 distinct read-only tool calls, accumulated about 395 KB, and hit context overflow without a header or Telegram reply. Finalization `fba6d9db...` failed closed `response_invalid`; no binding, delegation, worker, or native-child evidence exists.
- Failure artifacts `d4e177d8...` / `31f86489...` and transcript `7a6addc6...` remain retained and must not be retried unchanged. Provider telemetry supplied no actual answering model.
- The Agency-only ADR-0167 repair correlates failed `agent_end` to one exact final `isError` payload for 30 seconds, persists only terminal category/hash evidence, and leaves normal answer/header/child gates unchanged. Wrong identity, stale marker, replay, malformed receipt, and bridge failure remain blocked; a later success clears an earlier failure marker.
- The native-error candidate passed 251 / 1 intentional skip plus Ruff/docs/diff and independent review. Clean checkout `484fe2de` installed Agency only as `6ede7fad...`; plugin/runtime integrity, 12 hooks, routes, Store schema 47, 15 contractors, channels, and untouched Hermes were verified.
- Post-install `/new` delivered exact acknowledgement in fresh session `447738d1...`; redacted artifact SHA is `8fea7044...`.
- Exact first `agency status` created run `a4b27543...`, trace `7e7a6318...`, and abstained routing `f7bc2f7e...`. Agency recorded `openclaw-operations` row `3b9037a9...` and appended the updated header to the awaited tool result, but native `task-general` authored the stale initial header with `Skills loaded: none`.
- Finalization `25cf1630...` correctly closed `response_invalid` with `skills_loaded` missing; Telegram queued no reply. There are zero Agency model receipts, specialists, resident bindings, workers, native-child rows, or delegation rows. Transcript / trace / redacted artifact SHAs are `78d096d5...` / `6c9bc3bc...` / `9a9e2a35...`.
- Repair `d7187e80` was installed from clean ledger `456a75b7` as Agency-only operation `fa68e6a4...`: runtime `573a6a14...`, launcher SHA `d65af026...`. Native restart is RPC-green with zero restarts, 12 hooks, and both channels connected; native routes and Agency/Hermes hashes are unchanged.
- Fresh session `6360c186...` passed exact status as run `86f838f0...`, trace `ad834646...`, abstained routing `a67e66ad...`, and terminal `d84fc7d8...`. Telegram delivered the exact deterministic header: `agency-steward / none / none / requested execution alias task-general / deterministic`.
- Changed `node-connect` run `25fa081a...`, trace `c1bbbdc7...`, routing `3548700e...`, specialist row `8e538079...`, skill row `d02c71ae...`, and terminal `6907ed38...` correlate the delivered header `agency-steward, code-reviewer / none / node-connect / workforce inference task-agency-router -> linux-task-agency-router/task-agency-router wrapper / inference`. Three applied receipts prove automatic `openclaw` harness/profile selection, exact alias/model-group, LiteLLM, zero fallback, and Telegram delivery.
- Changed substantive run `72314429...`, trace `50c11095...`, routing `21b8b545...`, specialist rows `4bb8ce63...` and `1707c674...`, and terminal `803465de...` correlate its exact delivered header: `agency-steward, section-508-accessibility-specialist, ai-evaluation-engineer / none / none / workforce inference task-agency-router -> linux-task-agency-router/task-agency-router wrapper / inference`.
- The substantive turn retained four provider attempts: three applied and one contract-invalid, all on the same OpenClaw profile; cross-provider fallback is zero. No delegation, worker, or native-child evidence exists. Actual answering model remains unavailable because the LiteLLM callback is absent. Final transcript SHA is `93dcbc...`.
- Final Store backup SHA `02a76504...` has integrity `ok`, schema 47; contractors remain 15. Runtime/launcher/config and protected-host invariants remain unchanged. OpenClaw host-scoped acceptance now passes; Rule 4/delegation is not proven and no matrix cell moved.
- Hermes install/activation evidence and its retained `mcp` host-attribution defect remain unchanged. Hermes is the only next host package.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- Earlier failures remain retained; Rule 4 native-child delivery/delegation is unproven and no matrix cell moved.
- Hermes installation, parent activation, header, and skill evidence pass; correct native-host attribution and substantive Agency routing remain pending.

## exact-blocker

OpenClaw has no remaining host-scoped blocker. Hermes still needs corrected native-host attribution and substantive Agency routing; preserve all earlier failed evidence.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Continue Hermes only, preserving its effective home and native inventory.
2. Prove corrected Hermes attribution, exact Agency routing, Store correlation, and delivery without changing native routes.
3. Do not claim Rule 4 or move the matrix without native-child delivery evidence.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and do not retry unchanged code/state.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change or Codex canary belongs in this package.
