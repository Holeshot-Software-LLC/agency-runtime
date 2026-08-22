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
evidence_commit: 1b789ac3b66c8e3e3e74e3a16bc66667c07cd517
minimum_ledger_commit: 6d6ea5718aea2698916149467e96fa934adbd457
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Clean dedicated worktree `codex/ar119-openclaw-hermes-litellm` is at AR-273 ledger `6d6ea571`; repaired AR-264 anchor `f76050d7` is an ancestor.
- Latest online pre-install Store backup has integrity `ok` and SHA-256 `d0098af5056bdc54055f20b1fb3e59f2efdc1111c9abb6215c2b78d8104f1300`. The bounded Agency install retained 15 contractors.
- OpenClaw stayed on audited `2026.7.1-2`, native primary `litellm/task-general`, six fallbacks, 21 LiteLLM models, and its existing channel configuration. The host package and native inference configuration were not reinstalled or changed.
- Agency-only install `4dd7ee41-121f-4cde-a391-9cecd0665d72` installed AR-273 bundle `51320b45f63cc68db52b267928c1939ab908052f623900a51786228c5b978419`. Launcher SHA-256 is `755ec953638d85b175f1b4aa705e9cc388cde3d5011520a6bfc7f2986528a78c`; runtime digest is `c71fbb41ca8780b5e5a5424ef240dbf92bdf56a36dbc9d2caac70dcfa22d3497`.
- New first-message control session `b610efe7-4e71-43c7-8011-fb13f2736f2b`, trace `de166bdc-d649-462d-996b-b2b030a34a8e`, and run `c5e8d0bd-99b5-431c-9bb3-6bead5d2eeef` completed with accepted finalization `cbc9107f-a34a-4fad-b919-17f3e1ae1d44`. Deterministic abstention proves control activation/final delivery, not workforce inference.
- The next harmless skill work unit was retained as failed: trace `9384d3a3-0a28-4150-a8fa-ab493efda7bf`, run `a5504721-0aa9-4fa3-98df-f5667c933b5b`, failure receipt `3193483a-712b-4c1d-8f13-ccb6799433a1`, reason `workforce_inference_failed`. It created no skill, specialist, routing, finalization, or model-receipt row and was not retried.
- Both inference attempts automatically selected harness `openclaw`, profile/provider name `linux-task-agency-router`, provider type `litellm`, and exact requested model/model-group `task-agency-router`. Both failed `provider_response_contract_invalid`; no Codex, Claude, or other fallback occurred.
- AR-273 proves the contract failure is in Agency's generic HTTP payload, not the operator-owned alias mapping: LiteLLM/OpenAI-compatible calls omitted the supplied closed schema and LiteLLM omitted configured reasoning effort. The alias echo remains distinct from an actual answering-model receipt, and the proxy still has no Agency callback.
- Six focused red assertions preserve the missing schema/reasoning behavior. The minimal model-agnostic repair delivers the deterministic bounded schema in the trusted system instruction and sends LiteLLM `reasoning_effort`; exact regressions pass 7/7 and the affected warning-strict inference slice passes 134/134. No validator, retry, fallback, host, alias, or proxy configuration changed.
- Slack and Telegram report configured/running with no current error, but no new Telegram Store run has arrived since the local proof. Hermes stayed running and untouched as break glass. Codex OAuth/config/canary, Claude, and ZCode were untouched.

## completed-evidence

- Repository/bootstrap identity, online Store backups, redacted host inventories, Agency install provenance, config invariants, control response delivery, failed provider attempts, and protected-host hashes are retained.
- AR-272 native finalization is proven. Successful skill loading and substantive Agency workforce inference remain unproven because the exact alias response fails the strict planner contract.
- AR-273 is locally green and installed. Fresh substantive trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`, run `c080b393-72fd-4133-9485-d3e786e6c90a`, and receipt `de5f98bc-ca21-4b9b-b881-d862bf5b4da8` retain one `provider_no_valid_response` attempt through the exact OpenClaw profile/alias with zero fallback. LiteLLM returned HTTP 200, but no valid Agency object, routing, finalization, skill, specialist, or model row exists.
- Focused OpenClaw tests pass 65/65; the earlier production spine passed 827 with three skips. No hosted workflow, push, PR, tracker mutation, host canary, or matrix movement occurred.

## exact-blocker

1. Do not remap the shared proxy, guess a target-specific request shape, retry unchanged input, or weaken Agency validation.
2. A direct content-free response-shape diagnostic requires explicit owner approval to reuse the OpenClaw process credential in memory; the rejected attempt sent no request and exposed no value.
3. After exact classification, add a focused red test and smallest general repair, reinstall only Agency, and use a genuinely new work unit. Telegram `/new` plus exact `agency status` remains an operator-delivery prerequisite; Hermes remains outside this package.
4. AR-265 through AR-273 tracker creation remains pending separate outward-write authorization.

## same-task-continuity

Continue with OpenClaw only after the credential decision. Hermes is running break glass and remains outside this package. Do not retry a consumed prompt or receipt unchanged.

## next-bounded-work-package

1. Classify the successful HTTP envelope without retaining response content or credential data.
2. Test and implement only the precise general parser/transport repair, then reinstall Agency's OpenClaw integration and run a different non-mutating work unit plus conditional harmless-skill proof.
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
