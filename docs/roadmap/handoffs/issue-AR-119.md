---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-23
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

- Branch `codex/ar278-openclaw-one-pass` is at clean failure-evidence ledger checkpoint `bdc3025f`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- Agency-only OpenClaw install `97fd0d49-e833-458a-a4b6-fb818761f212` binds bundle `97f95751...`, runtime `145ac94d...`, and launcher SHA `9adc2a85...`. The installer left the gateway stopped; native restart is RPC- and Telegram-probe-green with zero restarts.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected-host route changed.
- The differing reset-session repair delivered `/new` with one-use consumption. Fresh session `130e58cd...` completed exact status as trace `58bce9a1...`, terminal `9d7d7372...`, and `openclaw-operations` row `b2d2f4b8...`; its deterministic header and Telegram delivery pass.
- The required exact restart-safety request then failed as run `324dcb7c...`, trace `755985e5...`. Agency routing `436eaef9...` selected `ai-evaluation-engineer` and `ai-data-remediation-engineer`; matching specialist rows and `openclaw-operations` row `ef7b8440...` exist.
- Three successful wrapper receipts selected host `openclaw`, profile `linux-task-agency-router`, and exact requested alias/model-group `task-agency-router`. Receipt ordinals `2/1/0` are attempt enumeration, not provider fallback; cross-provider fallback is zero. Provider telemetry supplied no actual answering model.
- The native `task-general` parent made 30 tool-only model calls and 108 distinct read-only tool calls, accumulating about 395 KB of results before OpenClaw stopped it for context overflow. No natural response or Agency header was authored; Telegram queued no reply and reported no channel error.
- Agency failed closed: finalization `fba6d9db...` atomically closed the run `response_invalid` with all five header fields missing. There is no resident binding, delegation, worker, activation, native-child, or delivery-verification row.
- Redacted failure artifacts have SHAs `d4e177d8...` and `31f86489...`; final native transcript SHA is `7a6addc6...`. The attempt is retained and must not be retried unchanged.
- The Agency-only ADR-0167 candidate is locally complete but not installed. It correlates failed `agent_end` to one exact final `isError` payload for 30 seconds, persists only terminal category/hash evidence, and leaves normal answer/header/child gates unchanged. Wrong identity, stale marker, replay, malformed receipt, and bridge failure remain blocked; a later success clears an earlier failure marker.
- Focused OpenClaw repair tests pass 251 / 1 intentional skip; full repository Ruff check/format, docs checks, and diff check pass. Independent security review found no blocker. No host or config was mutated by this candidate package.
- Store integrity remains `ok`, schema 47, contractors remain 15, and launcher SHA remains `9adc2a85...`. OpenClaw and Hermes services remain active; Hermes stays untouched as break-glass.
- Hermes install/activation evidence and its retained `mcp` host-attribution defect remain unchanged in the verification packet. Correct Hermes attribution and substantive Agency routing are pending until OpenClaw passes.

## completed-evidence

- OpenClaw reset, activation, exact status header, skill row, and Telegram delivery pass. Substantive Agency inference succeeded, but native parent completion/header/delivery failed and remains pending.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- This package does not prove Rule 4 native-child delivery and does not move an AR-119 matrix cell.
- Hermes installation, parent activation, header, and skill evidence pass; correct native-host attribution and substantive Agency routing remain pending.

## exact-blocker

The exact restart-safety input is terminally retained and cannot be retried unchanged. Commit and install the locally verified Agency-only candidate into natively stopped OpenClaw, then use a fresh session and a genuinely new bounded read-only work unit before touching Hermes.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Commit the repair/recovery pair, back up live state, and install Agency only into natively stopped OpenClaw.
2. Start one fresh OpenClaw session, re-prove exact status first, then send a changed substantive request capped at three read-only calls and excluding the broad native skill.
3. Preserve Store/provider/header/Telegram evidence; only after OpenClaw passes, reinstall Hermes and prove native attribution plus `task-agency-router` routing.

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
