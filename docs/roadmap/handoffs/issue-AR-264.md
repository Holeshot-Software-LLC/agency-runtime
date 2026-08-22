---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-22
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
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 7fcd828d2a20d85562bee73cbea9f538985107ac
minimum_ledger_commit: 7d0460a317c3f2528ebaceb5284b8020b63aa431
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Clean branch contains repair `7fcd828d`, ADR-0165, and their ledger commits; `f76050d7` remains an ancestor.
- Online Store backup has integrity `ok`, schema 47, 15 active contractors, and SHA `bdf3c4d6bfedf74251319a9c587b0b64815d35b6a74b15c9f2b65aa18cedb5ff`.
- OpenClaw remains audited `2026.7.1-2` on native `litellm/task-general`, six fallbacks, and 21 LiteLLM models. Only `/meta/lastTouchedAt` changed; the host package, native model routing, channels, and alias target were not changed.
- The first install refused the untrusted virtualenv before mutation. A changed trusted `/usr/bin/python3` input imported this checkout and completed without weakening safety.
- Agency-only install `3aac2a46-e638-46d6-812d-d2df2ea3aa0b` installed bundle `69783cf41a5e68a25b650aaaf2869ca370b1aefa3123d918e612d6910c376f72`. Launcher SHA is `f6962d190ee366d44724691fb01204c79bed3217ee615e83da6be7022845eb36`; runtime digest is `6afbaf655371ae1007d3817baebb188f379c10f4b45ff8c8fe0c67503335adcb`.
- Fresh exact-status session `fe3ab39c-fea0-4974-82b2-c85478b10b8a`, trace `3b26c907-2c9d-4240-8160-8c6d7cce6a08`, run `7d9e7bc3-3268-419e-8358-a3ef2ccf93c7`, and accepted finalization `97eaacb8-9dcf-4431-8150-0e1d702e8ce3` are hash-matched to the native transcript. Deterministic abstention proves control/final delivery, not workforce inference.
- The consumed pre-repair skill and substantive failures remain retained and were not retried. Their exact harness/profile/alias selection plus the content-free diagnostic, expected-red, and green slices preserve the AR-273 repair chain.
- New trace `402e37f5-f38e-425b-95c6-62e911be2566` and run `4963f31f-e114-4fa0-b051-8ded1ded51a1` completed. All three structured stages automatically selected harness `openclaw`, profile `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected provider identity appears.
- Routing `982f6c68-ac38-41a3-a84a-b7b60bee39cb` accepted and specialist rows `80c52f54-3390-4f06-81e1-0ddca89ebe27` plus `866003fb-e74a-491c-a422-1ea64dd4c677` loaded. Finalization `cfb2e3de-9a2b-4fda-9194-6edcb52ca3a5` delivered a native response whose hash matches the Store. Alias wrapper receipts provide no actual answering model, so none is claimed.
- AR-274 now authorizes native reads only against exact eligible/model-visible inventory and is installed. Focused tests pass 22/1 skipped and the affected slice 453/1 skipped; fresh different skill evidence remains pending.
- Gateway/RPC and the plugin are green. Slack is connected/probe-green; Telegram is configured/running and probe-green but reported connected=false immediately after restart. Hermes and LiteLLM stayed active; protected hosts were untouched.

## completed-evidence

- Repository/bootstrap identity, online Store backups, redacted host inventories, Agency install provenance, config invariants, control response delivery, failed provider attempts, and protected-host hashes are retained.
- AR-272 finalization and AR-273 structured workforce inference remain proven. The accepted roster is Store-backed; the newly installed AR-274 bridge still needs fresh skill evidence.
- Every failed provider and installer attempt remains retained. The distinct status, skill, and substantive turns are next.
- No hosted workflow, push, PR, tracker mutation, host canary, or matrix movement occurred.

## exact-blocker

1. Run exact-status as the first message of a completely fresh session and retain its native artifact.
2. Run a genuinely different harmless skill and substantive work unit; correlate Store/header/profile/provider/alias evidence without invention.
3. Telegram `/new` remains operator proof; AR-265 through AR-274 tracker creation remains pending authorization.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Preserve the fresh exact-status response and transcript.
2. Correlate a different skill and substantive work unit through Store/header/provider evidence.
3. Recheck Telegram and protected hashes; keep the alias target and all break-glass/proven hosts untouched.

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
