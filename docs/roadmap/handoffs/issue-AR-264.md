---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-23
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
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar278-openclaw-one-pass
evidence_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
minimum_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` is clean at checkpoint/ledger pair `f96065e6` / `c0426ab9`; implementation/ledger pair `e5ae8de1` / `7abf9b13` contains the correlation repair and `f76050d7` remains an ancestor.
- Agency-only install `251c4349-f7e3-4640-980d-055b857c0abe` completed with 15 unchanged contractors, bundle `ba344b92...`, runtime `70239e65...`, and launcher `3090708c...`; the installer left OpenClaw stopped.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six fallbacks. Agency remains scoped to `linux-task-agency-router`, LiteLLM, and exact alias/model-group `task-agency-router`. OpenClaw config changed only its timestamp; protected-host routing is unchanged.
- Native restart loaded 11 hooks including `before_tool_call`, awaited OpenClaw middleware, no Agency tool, and zero diagnostics. RPC, Telegram, and Slack probes are green; the gateway credential variable is populated without its value being emitted.
- Sixth fresh exact status turn passed in native session `5570abb9-eecc-4d77-be4b-bb9636bdf886`. Trace `78a68fdc-e192-4098-b8c7-58d20cf3bd8a`, run `6f446944-da85-4eda-8049-227bf268775e`, routing `da98bac1-c78a-4be7-9a6b-a121386fdaf7`, and terminal `9398965e-550c-452d-9f85-3e59f2ecd029` correlate.
- Finalization accepted with no missing fields, the run completed, and Telegram outbound followed inbound. Response SHA is `1e8c1df5...`; transcript SHA is `593ddef8...`.
- The header's `task-general` value is OpenClaw's parent request alias. Deterministic status created zero Agency model receipts, specialists, skills, or binding, so it does not prove `task-agency-router` or an answering model.
- A subsequent delivered read-only turn produced trace `6b18f9f0-a8bb-4a68-b70b-45ec7cdfe454`, completed run `afc905ca-f68b-40c7-b694-b1842e7277c7`, accepted routing `26492374-3d54-4da2-8bc6-0381e83813f4`, and terminal `d6ae9ade-b124-46b5-8822-7457a177f526`.
- Three Agency receipts prove profile `linux-task-agency-router`, LiteLLM, exact `task-agency-router`, and zero fallback. Actual answering model is unavailable; native parent `task-general` remains separate.
- The exact native-inventory-authorized `healthcheck` read produced no Store skill row and the header honestly stayed `none`. OpenClaw's middleware supplies arguments but no session/run callback context; the bridge failed closed. Expected-red exit 245 now models this exact gap.
- The installed OpenClaw-only repair carries one-use correlation from `before_tool_call`, rejects collisions, and passes 374 affected tests with 1 skip.
- Current pre-install online Store backup is integrity `ok`, schema 47, SHA `3cdf39fc...`; contractor count remains 15. Agency config SHA is unchanged at `43367ec9...`; OpenClaw's only semantic config delta is its timestamp.
- The first operator send after the current restart was not observed at OpenClaw's Telegram inbound edge and created no Agency trace. Native and Telegram API probes are healthy with zero queued updates; live skill proof therefore remains pending. Hermes remains break glass; Codex OAuth/config/canary, Claude, and ZCode remain untouched.

## completed-evidence

- Self-contained OpenClaw Agency activation, final-only delivery, Store terminal correlation, and host-owned Telegram outbound now pass.
- Install/launcher provenance, contractor preservation, config invariants, and before/after Store integrity are current.
- AR-273 remains the prior workforce-alias proof; the new status control is not misreported as inference.
- The delivered second turn independently proves exact Agency alias routing with zero fallback while retaining skill capture as a failure.

## exact-blocker

1. Restore observable Telegram inbound without changing native host configuration and establish a fresh session.
2. Prove the eligible `tmux` read and matching Store/header evidence without delegation.
3. Prove the exact substantive review and preserve final integrity/config evidence before Hermes.

## same-task-continuity

Continue with OpenClaw only from this checkpoint. Hermes remains outside the current mutation boundary.

## next-bounded-work-package

1. Finish the clean implementation/ledger checkpoint.
2. Reinstall Agency only into natively stopped OpenClaw, restart natively, and use a fresh session plus a different harmless skill.
3. If skill proof passes, send the exact restart-safety review and checkpoint the completed OpenClaw bundle.

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

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Never expose credential values or channel/user numeric identifiers.
- Do not run unsupported host canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
