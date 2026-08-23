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
evidence_commit: 620b8f19f2ccacf686bac0a252b6772ea470dabd
minimum_ledger_commit: 2fd2aede12f4c8f74b780f562a8b2792c9829bf4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- The active branch is `codex/ar278-openclaw-one-pass`, based on clean AR-119 checkpoint `8d707a2b`; current `origin/main` is `4a326773` and `f76050d7` remains an ancestor. Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 with native primary `litellm/task-general` and its six original fallbacks. Agency's harness-scoped profile remains `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, base `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No native or protected-host route changed.
- Three Telegram failures remain retained. Traces `9ac12abc...`, `2eaaf8e9...`, and `4552b87d...` prove respectively silent suppression, a premature text-hash/full-envelope conflict, and successful exact Agency LiteLLM routing followed by native `NO_REPLY`. None queued a Telegram response.
- The latest Agency-only install is `87b518e8...`, bundle `7f94acf0...`, runtime `1816b6ad...`, launcher `c34c66be...`, schema 47, and 15 contractors. The plugin is currently registered/staged but natively disabled. Gateway RPC and Telegram/Slack probes are green.
- Ordinary recovery passes: exact Telegram request `reply with pong` received exact `pong`; redacted inbound/outbound facts and native artifact SHA `0420d72c...` are retained. This is not Agency acceptance.
- The earlier claim that OpenClaw needs a new return-direct API is corrected. A terminal tool-use event is classified `non_deliverable_terminal_turn`, but the supported awaited `registerAgentToolResultMiddleware` surface can refresh Store evidence before the next model step.
- ADR-0166 selects an OpenClaw-only path: preflight supplies the initial exact five-line snapshot; one awaited tool-result middleware records native tool evidence and appends the updated exact snapshot while preserving the tool result; the model emits one natural first response; existing final validation and full-payload authorization remain unchanged. The generated OpenClaw plugin no longer exposes `agency_finalize`.
- Expected-red exit 232 is retained. The focused security, adapter, and installer slice passes 72 tests, including no fabricated refresh, honest disabled state, and installer refusal without the middleware contract. The proportionate header, Store, inference, registration, and policy gate is 289 passed, 2 skipped. The candidate is not installed.
- Hermes remains the running break-glass host. Codex OAuth/config/canary, Claude, and ZCode remain untouched. No host canary, child-delivery claim, matrix movement, push, PR, tracker mutation, or hosted workflow occurred.

## completed-evidence

- Starting identity, Store backups, redacted inventories, credential-name presence, install/launcher provenance, config invariants, and every failed live turn are retained.
- AR-273 proves exact OpenClaw harness/profile/provider/alias selection on the free 14B target without protected-host fallback; actual backing-model telemetry remains unavailable.
- AR-274 native skill evidence, AR-276 preflight gating, AR-277 first-pass terminal behavior, reset correlation, and ordinary Agency-disabled delivery remain proven within their exact scopes.
- ADR-0166 and 72 focused tests now establish the local OpenClaw natural-first-pass candidate. They do not establish live Telegram delivery or Rule 4 child delivery.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. The OpenClaw-only candidate is locally green but not installed. Fresh host-written Telegram delivery with correlated Store evidence remains the AR-278 acceptance gate.
2. Repository policy requires the substantive/ledger checkpoint before live mutation. Then Agency Runtime, not OpenClaw, must be installed into the natively stopped gateway without changing either native models or Agency inference routing.
3. Hermes remains break glass and outside this package.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Finish local documentation/lint checks and create the clean substantive/ledger checkpoint.
2. Reconfirm backups and invariants, stop OpenClaw natively, install Agency Runtime only from this checkout, and restart OpenClaw natively.
3. Use a completely fresh Telegram session and genuinely new inputs; preserve the first response before skill and substantive proof. Keep Hermes and every protected host untouched.

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
