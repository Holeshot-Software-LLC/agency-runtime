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
evidence_commit: 71cb09751bc3b1f81cf4e0312765c616c305780c
minimum_ledger_commit: a518ed236b71774f218b6dff92222d9e4c53144c
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` has clean pair `71cb0975` / `a518ed23`; `f76050d7` remains an ancestor.
- Agency-only install `c3b124d6-6a88-46b4-8c5a-706c5187457b` completed with 15 unchanged contractors, bundle `fcc48773...`, runtime `0b05a499...`, and launcher `317045e7...`; the installer left OpenClaw stopped.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six fallbacks. Agency remains scoped to `linux-task-agency-router`, LiteLLM, and exact alias/model-group `task-agency-router`. OpenClaw config changed only its timestamp; protected-host routing is unchanged.
- Native restart loaded ten hooks, awaited OpenClaw middleware, no Agency tool, and zero diagnostics. RPC, Telegram, and Slack are green; the gateway credential variable is populated without its value being emitted.
- Sixth fresh exact status turn passed in native session `5570abb9-eecc-4d77-be4b-bb9636bdf886`. Trace `78a68fdc-e192-4098-b8c7-58d20cf3bd8a`, run `6f446944-da85-4eda-8049-227bf268775e`, routing `da98bac1-c78a-4be7-9a6b-a121386fdaf7`, and terminal `9398965e-550c-452d-9f85-3e59f2ecd029` correlate.
- Finalization accepted with no missing fields, the run completed, and Telegram outbound followed inbound. Response SHA is `1e8c1df5...`; transcript SHA is `593ddef8...`.
- The header's `task-general` value is OpenClaw's parent request alias. Deterministic status created zero Agency model receipts, specialists, skills, or binding, so it does not prove `task-agency-router` or an answering model.
- Pre/post Store backups are integrity `ok`, schema 47, SHAs `d00c86f9...` / `470aa2fd...`; contractor count remains 15. Hermes remains break glass; Codex OAuth/config/canary, Claude, and ZCode remain untouched.

## completed-evidence

- Self-contained OpenClaw Agency activation, final-only delivery, Store terminal correlation, and host-owned Telegram outbound now pass.
- Install/launcher provenance, contractor preservation, config invariants, and before/after Store integrity are current.
- AR-273 remains the prior workforce-alias proof; the new status control is not misreported as inference.

## exact-blocker

1. Prove one harmless eligible skill read and matching Store row without delegation.
2. Prove the exact substantive review through `linux-task-agency-router` and `task-agency-router` with zero protected fallback.
3. Preserve final integrity/config evidence before beginning Hermes.

## same-task-continuity

Continue with OpenClaw only from this checkpoint. Hermes remains outside the current mutation boundary.

## next-bounded-work-package

1. Send the harmless `healthcheck` skill-read request in the current fresh session.
2. If delivery and Store skill evidence pass, send the exact OpenClaw restart-safety review.
3. Correlate provider receipts and checkpoint the completed OpenClaw bundle.

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
