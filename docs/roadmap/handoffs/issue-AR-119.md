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

- Branch `codex/ar278-openclaw-one-pass` has clean implementation/ledger pair `e5ae8de1` / `7abf9b13`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- Agency-only install `c3b124d6-6a88-46b4-8c5a-706c5187457b` completed from clean checkout `a518ed23` while OpenClaw was stopped. Bundle `fcc48773...`, runtime `0b05a499...`, and launcher SHA `317045e7...` bind to that checkout. The installer did not restart the host.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six original fallbacks. Its current config differs from exact pre-install SHA `0f30f12d...` only at `meta.lastTouchedAt`; models, providers, channels, and credential indirection are identical.
- Native restart is RPC-green. Agency is enabled, loaded, imported, and activated with ten hooks, `agentToolResultMiddleware=[openclaw]`, no tool, and zero diagnostics. Telegram and Slack are configured/running/probe-green. The gateway has populated `LITELLM_API_KEY`; its value was never emitted.
- Agency remains harness-scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, and 120000 ms. The existing global default is `agency-default`; Codex/Claude/ZCode have no new harness override. Hermes remains uninstalled break glass.
- Five no-outbound Telegram failures remain retained. The installed correlation repair then passed a sixth fresh exact `agency status` turn in native session `5570abb9-eecc-4d77-be4b-bb9636bdf886`.
- Store trace `78a68fdc-e192-4098-b8c7-58d20cf3bd8a`, run `6f446944-da85-4eda-8049-227bf268775e`, routing `da98bac1-c78a-4be7-9a6b-a121386fdaf7`, and terminal `9398965e-550c-452d-9f85-3e59f2ecd029` correlate. The run completed; finalization accepted with no missing fields; Telegram outbound followed inbound.
- The exact 489-character response has SHA `1e8c1df5...`; transcript SHA is `593ddef8...`. Its five-line header records `agency-steward`, no delegation, no skill, `requested execution alias: task-general`, and deterministic recruitment.
- `task-general` is the OpenClaw parent request alias for this control response. The trace has zero Agency model receipts, specialists, skills, or resident binding. Deterministic status did not invoke or prove `task-agency-router`; no answering model is claimed.
- A new read-only skill turn then completed and delivered under trace `6b18f9f0-a8bb-4a68-b70b-45ec7cdfe454`, run `afc905ca-f68b-40c7-b694-b1842e7277c7`, routing `26492374-3d54-4da2-8bc6-0381e83813f4`, specialist `5b2f0fbd-445d-41f5-9d4c-1e2a99f3ff09`, and terminal `d6ae9ade-b124-46b5-8822-7457a177f526`.
- Its three Agency receipts prove OpenClaw profile `linux-task-agency-router`, provider type `litellm`, exact alias/model-group `task-agency-router`, and zero fallback. Actual answering model remains unavailable. Native parent routing separately remained `task-general`.
- OpenClaw read the exact inventory-authorized `healthcheck` path, but Store skill count stayed zero and the honest header said `Skills loaded: none`. Installed source proves the awaited middleware omits session/run context; Agency's prior generated test invented it, so the bridge failed closed. Failure artifact SHA is `c742cbe4...`.
- Expected-red exit 245 now matches the host contract. The OpenClaw-only candidate carries bounded one-use correlation from `before_tool_call`, rejects collisions, and passes 374 affected tests with 1 skip. It is not installed.
- Pre-install Store backup SHA `d00c86f9...` and post-status backup SHA `470aa2fd...` both have integrity `ok`, schema 47; contractors remain 15. Hermes, Codex OAuth/config/canary, Claude, and ZCode remain untouched.

## completed-evidence

- AR-278 status delivery now passes end to end: self-contained Agency middleware, natural parent response, both final gates, completed Store terminal, and host-owned Telegram outbound.
- Install provenance, exact config-path-only drift, plugin/middleware activation, credential-name presence, contractor preservation, and before/after Store integrity are retained.
- The requested `task-agency-router` alias remains configured only for Agency workforce inference. This deterministic control is deliberately not used as inference evidence.
- The delivered second turn now proves automatic OpenClaw workforce routing through that exact Agency profile and alias with zero protected fallback; skill evidence remains failed, not waived.

## exact-blocker

1. Checkpoint and install the OpenClaw-only tool-correlation candidate into natively stopped OpenClaw; do not reinstall OpenClaw.
2. In a fresh session, prove a genuinely different eligible native skill and matching Store/header evidence without delegation.
3. Run the exact substantive OpenClaw review, preserve final integrity, and checkpoint before starting Hermes.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Finish the clean implementation/ledger checkpoint for bounded native tool correlation.
2. Stop OpenClaw natively, reinstall Agency only, restart natively, and use a fresh session plus a different harmless skill.
3. If Store/header skill evidence passes, send the exact restart-safety review and finalize the OpenClaw evidence bundle.

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
