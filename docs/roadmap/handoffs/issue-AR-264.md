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
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 2d7c055a28ec0dea609a88a7229d20a559dfddad
minimum_ledger_commit: a70131d63c511e418edcda2ccae1f8e45866a95a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Clean dedicated worktree `codex/ar119-openclaw-hermes-litellm` is based on fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`; repaired AR-264 anchor `f76050d7` is an ancestor. Recovery anchor is `2d7c055a` plus ledger `a70131d6`.
- Latest online SQLite backup and live Store both have integrity `ok`; backup SHA-256 is `64421c3fc50623940930d757f15f7cd5930537ea9f8d9dd682a5ca771c8ea66d`. The bounded Agency install retained 15 contractors before and after.
- OpenClaw stayed on audited `2026.7.1-2`, native primary `litellm/task-general`, six fallbacks, 21 LiteLLM models, and its existing channel configuration. The host package and native inference configuration were not reinstalled or changed.
- Agency-only install `479c1a47-7e89-4091-a0f4-548f6913db58` completed from this checkout, installed native `agency_finalize`, changed no contractors, and did not restart the gateway. Launcher SHA-256 is `5539744ef47aa464921887ee067e3f3c54c9caeacac252259f5a5bb008d462cb`; runtime digest is `52724f5a8803d1662228a67c03c9a986a5eeebc2289ddb68cdad0306272de066`.
- Exact first-message local control completed in session `ba9ea05a-3694-4725-b2ea-0357bd16a112`, trace `c2574ce1-b81b-4e29-b66a-06293c6dde85`, run `aedb79d3-79d9-428c-9eb3-90dbc8aac8c9`. Finalization `b0f9a0f4-8da2-4b54-b678-826b3a5b61bc` is labeled `host=openclaw`, and its response hash matches the native transcript. Deterministic abstention proves control activation, not workforce inference.
- The next harmless skill work unit was retained as failed: trace `9384d3a3-0a28-4150-a8fa-ab493efda7bf`, run `a5504721-0aa9-4fa3-98df-f5667c933b5b`, failure receipt `3193483a-712b-4c1d-8f13-ccb6799433a1`, reason `workforce_inference_failed`. It created no skill, specialist, routing, finalization, or model-receipt row and was not retried.
- Both inference attempts automatically selected harness `openclaw`, profile/provider name `linux-task-agency-router`, provider type `litellm`, and exact requested model/model-group `task-agency-router`. Both failed `provider_response_contract_invalid`; no Codex, Claude, or other fallback occurred.
- AR-273 proves the contract failure is in Agency's generic HTTP payload, not the operator-owned alias mapping: LiteLLM/OpenAI-compatible calls omitted the supplied closed schema and LiteLLM omitted configured reasoning effort. The alias echo remains distinct from an actual answering-model receipt, and the proxy still has no Agency callback.
- Six focused red assertions preserve the missing schema/reasoning behavior. The minimal model-agnostic repair delivers the deterministic bounded schema in the trusted system instruction and sends LiteLLM `reasoning_effort`; exact regressions pass 7/7 and the affected warning-strict inference slice passes 134/134. No validator, retry, fallback, host, alias, or proxy configuration changed.
- Slack and Telegram report configured/running with no current error, but no new Telegram Store run has arrived since the local proof. Hermes stayed running and untouched as break glass. Codex OAuth/config/canary, Claude, and ZCode were untouched.

## completed-evidence

- Repository/bootstrap identity, online Store backups, redacted host inventories, Agency install provenance, config invariants, control response delivery, failed provider attempts, and protected-host hashes are retained.
- AR-272 native finalization is proven. Successful skill loading and substantive Agency workforce inference remain unproven because the exact alias response fails the strict planner contract.
- AR-273 is locally green and awaits its below-threshold clean commit pair plus a fresh OpenClaw install/proof.
- Focused OpenClaw tests pass 65/65; the earlier production spine passed 827 with three skips. No hosted workflow, push, PR, tracker mutation, host canary, or matrix movement occurred.

## exact-blocker

1. Context telemetry is 31.8 percent remaining, so the AR-273 substantive/worklog checkpoint must be clean before live work.
2. Do not remap the shared proxy, inspect or guess a target-specific request shape, retry unchanged input, or weaken Agency validation.
3. After the checkpoint, install only Agency into the existing OpenClaw host and use a genuinely new work unit. Telegram `/new` plus exact `agency status` remains an operator-delivery prerequisite; Hermes remains outside this package.
4. AR-265 through AR-273 tracker creation remains pending separate outward-write authorization.

## same-task-continuity

After the recovery pair, continue with OpenClaw only. Hermes is a running break-glass host and remains outside this package. Do not retry a consumed prompt or failure receipt unchanged.

## next-bounded-work-package

1. Commit the AR-273 local repair and ledger, then fast-forward the persistent OpenClaw worktree.
2. Reinstall only Agency's OpenClaw integration and run one fresh non-mutating work unit plus conditional harmless-skill proof; correlate strict Store/provider evidence.
3. Preserve operator Telegram evidence when supplied. Keep the alias, Hermes, Claude, ZCode, Codex OAuth/model settings, and OpenClaw native inference configuration untouched.

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
