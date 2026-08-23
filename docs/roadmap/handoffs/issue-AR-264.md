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
evidence_commit: 620b8f19f2ccacf686bac0a252b6772ea470dabd
minimum_ledger_commit: 2fd2aede12f4c8f74b780f562a8b2792c9829bf4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- The active branch is `codex/ar278-openclaw-one-pass`, based on clean checkpoint `8d707a2b`; `f76050d7` remains an ancestor.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six original fallbacks. Agency's OpenClaw-only profile remains `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, and the free 14B alias target; no host or protected-harness routing changed.
- Existing exact status, native skill, substantive inference, provider, Store, reset, and three failed Telegram receipts remain canonical in the verification packet. They prove exact Agency alias selection and isolate the failures after Agency inference; actual backing-model telemetry remains unavailable.
- The latest Agency install `87b518e8...` is registered/staged but natively disabled. Gateway RPC and Telegram/Slack probes are green, schema remains 47, contractor count remains 15, and ordinary exact `pong` delivery passes with Agency disabled.
- OpenClaw's terminal tool-use classification rules out a terminating `agency_finalize` handshake. Its supported awaited tool-result middleware provides the missing pre-model continuation seam without a host source or config change.
- ADR-0166 records the OpenClaw-only candidate: initial exact Store snapshot at preflight, updated exact snapshot appended only after awaited tool observation, one natural first response, unchanged final validation/full-envelope authorization, and no exposed finalizer tool.
- Expected-red exit 232 is retained. The focused OpenClaw security, adapter, and installer slice passes 72 tests, including fail-closed installer proof when the middleware contract is absent. The proportionate gate is 289 passed, 2 skipped. The candidate is not installed.
- Hermes remains break glass. Codex OAuth/config/canary, Claude, and ZCode remain untouched. No child-delivery or matrix-cell claim moves.

## completed-evidence

- Agency-only installation, OpenClaw activation, exact-status finalization, native skill evidence, and harness-scoped LiteLLM alias selection remain proven within their recorded scopes.
- The free alias target has passed Agency planner/recruiter/critic contracts and OpenClaw parent routing; it is not promoted into an actual-model claim.
- ADR-0166 and 72 focused tests establish the local natural-first-pass candidate only. Fresh host-written Telegram delivery and post-live Store/config receipts remain pending.
- No hosted workflow, push, PR, tracker mutation, host canary, protected-host change, or matrix movement occurred.

## exact-blocker

1. The OpenClaw-only candidate is locally green but not installed; fresh Telegram response delivery remains unproven.
2. Complete the required local checkpoint, then install Agency Runtime only into stopped OpenClaw without changing host models or Agency inference routing.
3. Keep Hermes and every proven host untouched.

## same-task-continuity

Continue with OpenClaw only after the clean commit pair. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Finish proportionate gates and create the local substantive/ledger checkpoint.
2. Back up and recheck the live Store/config invariants, stop OpenClaw natively, install Agency Runtime from this checkout, and restart it natively.
3. Run fresh Telegram status, harmless skill, and genuinely new substantive proof serially; preserve every result and leave Hermes untouched.

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
