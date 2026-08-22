---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-21
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
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: fba12371f4bf004ffadd9356bb00787b00e6194f
minimum_ledger_commit: 6ad46fb4a1309b3b52396055a73274d2d5d670b9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Clean dedicated worktree is at repair `fba12371` plus ledger `6ad46fb4`; repaired AR-264 anchor `f76050d7` is an ancestor.
- Fresh online Store backup has integrity `ok`, schema 47, and SHA `731934b20258feacf7d8835a9ba8e32d41844cd5685eef8ca65ad3dc1d51734f`. Contractor count stayed 15.
- OpenClaw stayed on audited `2026.7.1-2`, native primary `litellm/task-general`, six fallbacks, 21 LiteLLM models, and its existing channel configuration. The host package and native inference configuration were not reinstalled or changed.
- Agency-only install `b526ecdc-a538-4797-a8e8-656ecb3b315b` installed bundle `94d87723b900387f9dbad0dda73613b449332c34683a4fd68674c0e354314a22`. Launcher SHA is `fe71017957b7060d7480fa80b222455b2cc69fe42d2f7b9c71e98ba65573b01b`; runtime digest is `71c917a91ed3527065447e6aa5ec4e36466d1710f7f5d0a41411a5ac585decda`.
- Fresh exact-status session `fe3ab39c-fea0-4974-82b2-c85478b10b8a`, trace `3b26c907-2c9d-4240-8160-8c6d7cce6a08`, run `7d9e7bc3-3268-419e-8358-a3ef2ccf93c7`, and accepted finalization `97eaacb8-9dcf-4431-8150-0e1d702e8ce3` are hash-matched to the native transcript. Deterministic abstention proves control/final delivery, not workforce inference.
- The consumed pre-repair skill and substantive failures remain retained and were not retried. Their exact harness/profile/alias selection plus the content-free diagnostic, expected-red, and green slices preserve the AR-273 repair chain.
- New trace `402e37f5-f38e-425b-95c6-62e911be2566` and run `4963f31f-e114-4fa0-b051-8ded1ded51a1` completed. All three structured stages automatically selected harness `openclaw`, profile `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected provider identity appears.
- Routing `982f6c68-ac38-41a3-a84a-b7b60bee39cb` accepted and specialist rows `80c52f54-3390-4f06-81e1-0ddca89ebe27` plus `866003fb-e74a-491c-a422-1ea64dd4c677` loaded. Finalization `cfb2e3de-9a2b-4fda-9194-6edcb52ca3a5` delivered a native response whose hash matches the Store. Alias wrapper receipts provide no actual answering model, so none is claimed.
- OpenClaw read the exact inventory-reported bundled Weather `SKILL.md`, but the bridge dropped `path` and the adapter recognizes only `skill_view`. The Store created no `skills_loaded` row and the honest header says `Skills loaded: none`; AR-274 owns this separate native skill-evidence defect.
- AR-274 must validate any candidate read against the exact eligible/model-visible native inventory entry and fail closed for arbitrary, lookalike, disabled, malformed, or inventory-unavailable paths. Existing filesystem, executable, finalization, and Store trust checks remain unchanged.
- Slack and Telegram remain configured/running with no current error, but no new Telegram Store run has arrived. Hermes stayed running and untouched as break glass. Codex OAuth/config/canary, Claude, and ZCode were untouched.

## completed-evidence

- Repository/bootstrap identity, online Store backups, redacted host inventories, Agency install provenance, config invariants, control response delivery, failed provider attempts, and protected-host hashes are retained.
- AR-272 native finalization and AR-273 live structured workforce inference are proven. The accepted specialist roster is Store-backed; successful skill loading remains unproven because the native read was not normalized.
- Prior HTTP-200 failures remain preserved beside the completed exact-schema follow-up. AR-274 is the only current code blocker before a fresh different skill proof and the distinct substantive risk-review turn.
- Focused inference and OpenClaw slices pass 134/134 and 104/104; the earlier production spine passed 827 with three skips. No hosted workflow, push, PR, tracker mutation, host canary, or matrix movement occurred.

## exact-blocker

1. Normalize only an inventory-authorized OpenClaw native skill read; do not accept arbitrary paths, remap the proxy, inspect its target for dispatch, retry unchanged input, or weaken Agency validation.
2. Reinstall Agency only, then use completely fresh sessions and genuinely different skill/substantive work units. Telegram `/new` remains operator proof; Hermes remains outside this package.
3. AR-265 through AR-274 tracker creation remains pending separate outward-write authorization.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Add positive and fail-closed regressions for inventory-authorized OpenClaw native skill reads.
2. Reinstall Agency only and correlate fresh status, different skill, and different substantive Store/provider/header proof without actual-model invention.
3. Preserve operator Telegram evidence when supplied. Keep the alias target, Hermes, Claude, ZCode, Codex OAuth/model settings, and OpenClaw native inference configuration untouched.

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
