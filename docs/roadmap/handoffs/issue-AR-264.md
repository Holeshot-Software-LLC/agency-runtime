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
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
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
evidence_commit: a0ff74d4e9b4cfe85b2b4fc30b595556e5331708
minimum_ledger_commit: 77bfd2aed518bef194e1074d432749ae86b0dd28
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
- Fresh exact-status session `94f92dc5-a0c5-44a7-bfa0-1663d948025e`, trace `e5b43276-ff90-43a7-923e-9956ac278816`, Store run `31a11c4d-7dff-4c6a-a643-ef082cdea36d`, and finalization `30625a68-a8a5-479f-8cae-07396eec05d8` prove activation and native final delivery. This deterministic control does not prove workforce inference.
- Fresh `healthcheck` trace `11707056-a490-4cbc-97b6-9a8e621caa79` completed routing `132ee9fa-5cb6-409b-9668-dea79014eac2`, skill row `3dd34973-d2f5-4b38-adcf-51191f374214`, and finalization `47c0a487-916a-42cb-9d97-54ee205a0a7f`. All three stages used OpenClaw profile `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected fallback or actual-model claim exists.
- Exact restart review trace `869ef22a-e1a5-4b7e-b024-6bf12aa371ea` and smaller trace `b325368f-22e2-4815-8d01-2e9d1c22c543` each rejected two strict planner contracts from the same alias with zero fallback. Receipts `7fba14ce-c3df-4459-8462-542f7272a426` and `fe0c2f6b-e9be-45a6-b15a-f450c7e8a154` are terminal evidence. The first Gateway timed out after native context overflow; the second unheaded answer is not Agency delivery.
- Store integrity remains `ok`, schema 47, and the install preserved all 15 contractors. Agency config, launcher, OpenClaw, Hermes, Codex, and Claude hashes remain unchanged from the checkpoint. Telegram and Slack are connected/probe-green; Hermes remains untouched break glass.

- AR-275 now retains exact allowlisted planner policy codes and one generic semantic code through routing/preflight receipts and switches the one existing repair attempt to a concise complete-plan system contract. Expected-red is retained and the repair is green.
- Recovery pair `a0ff74d4` / `77bfd2ae` adds ontology-bound schemas and the OpenClaw fail-closed input gate. Focused/affected suites pass 154 plus 65 cases; the 828-test spine, 134 UI tests, docs, ruff, routing evaluation, and diff checks pass.
- Agency-only install `ba074210-c785-4d61-a014-c2f86dfdb571` completed with bundle `3139ec9c...`, launcher SHA `b67bb589...`, runtime digest `facf8047...`, and 15/15 contractors. Only OpenClaw metadata timestamp changed; native model/provider/channel/alias configuration did not.
- OpenClaw is RPC-green and the plugin is loaded with its priority-1000 input gate. Telegram and Slack are connected/probe-green; Hermes and LiteLLM stayed active.
- Three changed Agency-only routes proved automatic OpenClaw harness selection and exact profile/provider/alias with zero fallback, but produced no accepted team: traces `52223cc2...`, `bd2feabc...`, and `71c4ad65...`. No post-reinstall native turn ran.
- Post-install Store backup integrity is `ok`, schema 47, SHA `64c65d70...`. The host-scoped Agency soft-off was not applied because it requires explicit approval to bypass enforcement.

## completed-evidence

- Agency-only install, OpenClaw activation, exact-status finalization, native `healthcheck` evidence, and harness-scoped LiteLLM alias selection are proven.
- Substantive acceptance is blocked at the configured alias target's strict planner contract; invalid native answers remain unaccepted and unqueued.
- No hosted workflow, push, PR, tracker mutation, host canary, alias-target change, protected-host change, or matrix movement occurred.

## exact-blocker

1. The unchanged alias target must satisfy strict planner and recruiter contracts within the fixed call/repair budget; endpoint, credential, profile, and alias selection are already proven.
2. No native substantive turn is allowed until a changed Agency-only route accepts. Consumed prompts remain forbidden.
3. Restoring native OpenClaw replies while blocked requires explicit approval for the reversible OpenClaw-only Agency soft bypass. Hermes and protected-provider configuration remain unchanged.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Await the owner's keep-enforcement versus host-scoped-soft-off decision.
2. After the alias target produces an accepted changed Agency-only route, use one fresh native OpenClaw session.
3. Correlate Store/header/finalization evidence; keep Hermes and protected hosts untouched.

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
