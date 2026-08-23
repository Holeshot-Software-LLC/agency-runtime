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
evidence_commit: a9276e00d1dc6862fb0f93085069c4fd5ff27ce9
minimum_ledger_commit: 4b1172be4a0912eb5d12ba7bb27cf6faf95fc5d8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` has installed clean pair `a9276e00` / `4b1172be`; `f76050d7` remains an ancestor.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six fallbacks. Agency remains scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, and the free target. No protected-harness route changed.
- Agency-only install `175adc13-ef5f-4286-ac39-0a7584e9a982` is active with bundle `7a36d4df...`, runtime `8ec95839...`, and launcher `30c5760b...`. Ten hooks, awaited OpenClaw middleware, no tool, zero diagnostics, RPC, Telegram, and Slack are green. OpenClaw config changed only its timestamp.
- Fifth fresh Telegram attempt: `/new` acknowledgement absent; exact `agency status` entered a new session; six native `task-general` calls and tools authored a 1274-character status response; no reply was queued.
- Trace `f946f532-4b53-4695-b660-36be48500dc3`, run `79a11206-3c58-4ed0-b2b8-121bf3d0fdb9`, routing `50c37f62-8278-4e35-99a2-7985b97cb4f9`, terminal `ae002770-f47f-4c84-890f-9ccfd37fd06b`, and transcript SHA `deeb9040...` correlate. Status was deterministic; no workforce inference, specialist, skill, binding, or model receipt was expected.
- The exact five-line requested-alias/deterministic header proves the alias-only receipt fix worked. Finalization still rejected only `actual_model_selected` because OpenClaw omitted `modelId` from final hooks even though it supplied `task-general` during preflight.
- Expected-red exit 17 captures the missing identity. The generated OpenClaw plugin now carries the bounded preflight model through pre-verify and outbound revalidation, then deletes it at the final gate under existing TTL/size/count/runtime controls. Focused tests pass 90 with 1 skip.
- Store integrity is `ok`, schema 47, contractor count 15, snapshot SHA `93dc0be2...`. Hermes remains break glass; Codex OAuth/config/canary, Claude, and ZCode remain untouched.

## completed-evidence

- Awaited middleware, natural first-pass authorship, alias-only evidence filtering, install provenance, channel health, and fail-closed finalization are live-proven in their exact scopes.
- AR-273 remains the substantive proof for Agency profile/provider/alias selection and zero protected fallback; deterministic status does not re-prove inference.
- The new change is generated OpenClaw plugin correlation only. Shared policy, other adapters, host source/config, routing, and safety gates are unchanged.

## exact-blocker

1. Checkpoint and install the preflight-model correlation fix.
2. Re-prove fresh host-written status delivery before skill or substantive inference.
3. Keep Hermes and protected hosts untouched.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Do not retry unchanged code/state.

## next-bounded-work-package

1. Complete focused/docs/lint gates and create the substantive/ledger pair.
2. Stop OpenClaw natively, reinstall Agency only, restart it, and recheck invariants.
3. Collect a fresh Telegram status response, then skill and substantive proof only after delivery passes.

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

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Never expose credential values or channel/user numeric identifiers.
- Do not run unsupported host canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
