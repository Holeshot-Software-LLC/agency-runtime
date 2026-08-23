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
evidence_commit: a9276e00d1dc6862fb0f93085069c4fd5ff27ce9
minimum_ledger_commit: 4b1172be4a0912eb5d12ba7bb27cf6faf95fc5d8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- The active branch is `codex/ar278-openclaw-one-pass`. Clean pair `a9276e00` / `4b1172be` is installed; `origin/main` remains `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six original fallbacks. Agency remains harness-scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No protected-host route changed.
- Agency-only install `175adc13-ef5f-4286-ac39-0a7584e9a982` installed bundle `7a36d4df...`, runtime `8ec95839...`, and launcher SHA `30c5760b...` while OpenClaw was stopped. Native restart is RPC-green; Telegram/Slack probes are green; Agency has ten hooks, awaited middleware scoped to `openclaw`, no exposed tool, and zero diagnostics.
- The reinstall changed OpenClaw config only at `meta.lastTouchedAt`; native models, providers, channels, and credential indirection remain unchanged. Store schema is 47, contractors remain 15, and post-failure integrity is `ok` with snapshot SHA `93dc0be2...`.
- Five Telegram failures are retained. The fifth used a new native session after an unacknowledged `/new`; exact `agency status` reached OpenClaw. Six successful `task-general` calls and native tools produced a natural 1274-character response, but the turn kernel again recorded `no queued reply payloads`. Transcript SHA is `deeb9040...`.
- Store trace `f946f532-4b53-4695-b660-36be48500dc3`, run `79a11206-3c58-4ed0-b2b8-121bf3d0fdb9`, routing `50c37f62-8278-4e35-99a2-7985b97cb4f9`, and terminal `ae002770-f47f-4c84-890f-9ccfd37fd06b` correlate. Control routing correctly abstained/deterministic; no specialist, skill, resident binding, or workforce inference was expected.
- The fifth response began with the exact requested-alias/deterministic five-line header, and the trace has zero model receipts. This proves the prior alias-only receipt fix worked.
- Finalization still failed closed on only `actual_model_selected`. OpenClaw supplies `modelId=task-general` during `before_prompt_build` but omits it from `before_agent_finalize` and final payload context. The header used preflight identity; validation received an empty model and expected `none observed`.
- Expected-red exit 17 retains the missing correlation. The OpenClaw generated plugin now stores the bounded preflight model beside its existing session/run context, reuses it for both pre-verify and outbound revalidation, and deletes it at the final payload gate. The same TTL, size, runtime-disable clearing, and maximum-entry bounds apply. Focused OpenClaw tests pass 90 with 1 skip.
- Hermes remains break glass. Codex OAuth/config/canary, Claude, and ZCode remain untouched. No host canary, child-delivery claim, matrix movement, push, PR, tracker mutation, or hosted workflow occurred.

## completed-evidence

- SQLite online pre-install backup, redacted inventories, config invariants, install/launcher provenance, and all five failed live attempts are retained.
- Live evidence proves the awaited middleware and alias-only receipt filter work: native tools continued, refreshed Store context reached the model, one natural final was authored, and no alias was promoted to an answering-model claim.
- The remaining failure is isolated to OpenClaw final-hook context losing the already-correlated preflight model identity. The new change is generated OpenClaw plugin state only; shared header policy, another adapter, host source/config, model routing, and outbound safety remain unchanged.
- AR-273 remains the current proof of exact Agency workforce profile/provider/alias selection without protected-host fallback. Deterministic status does not re-prove workforce inference.

## exact-blocker

1. The model-correlation fix and regression are locally green but not checkpointed or installed.
2. Create the substantive/ledger pair, stop OpenClaw natively, reinstall Agency only, restart it natively, and recheck all invariants.
3. Use a fresh Telegram session/status work unit only after the changed runtime is live. Hermes remains outside this package.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Record only credential variable names and populated booleans. Never expose values or channel/user numeric IDs.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.
- OpenClaw `model_call_ended` proves provider/requested model metadata, not LiteLLM's answering model. Its finalization hook also omits `modelId`; use the bounded preflight correlation, never invent a value.

## next-bounded-work-package

1. Run focused/docs/lint checks and create the clean substantive/ledger checkpoint.
2. Reinstall Agency only into stopped OpenClaw; verify provenance, config path-only diff, plugin/channel state, and Store integrity.
3. Collect a fresh Telegram status response before harmless skill and substantive proof.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and do not retry unchanged code/state.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_openclaw_adapter.py tests/test_security_turn_boundaries.py tests/test_installer_registration.py tests/test_native_installer.py -k openclaw -q
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
- Never expose credential values. Preserve hashes, variable names, and populated booleans only.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change or Codex canary belongs in this package.
