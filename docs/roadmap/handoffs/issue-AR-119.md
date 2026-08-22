---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-22
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: a0ff74d4e9b4cfe85b2b4fc30b595556e5331708
minimum_ledger_commit: 77bfd2aed518bef194e1074d432749ae86b0dd28
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Clean branch pair `a0ff74d4` / `77bfd2ae` is based on fetched `origin/main` `4a326773`; `f76050d7` is an ancestor. Agency 0.1.0 imports from this checkout.
- Agency profile `linux-task-agency-router` uses `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No protected-host route changed.
- SQLite-consistent pre/post Store backups have integrity `ok`, schema 47, 15/15 contractors, and SHAs `468b4754...` / `64c65d70...`.
- Agency-only install `ba074210-c785-4d61-a014-c2f86dfdb571` completed with bundle `3139ec9c...`, launcher SHA `b67bb589...`, and runtime digest `facf8047...`. OpenClaw itself was not reinstalled.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general`. Pre/post config SHAs `d30386ac...` / `97b18a21...` differ only at `/meta/lastTouchedAt`. Agency and Codex config hashes remain unchanged; Hermes, Claude, ZCode, and Codex OAuth/model/canary were untouched.
- OpenClaw is RPC-green. `agency-preflight` is enabled, activated, loaded with ten hooks and no diagnostics; preflight runs in priority-1000 `before_agent_run`. Telegram/Slack are connected and probe-green; Hermes/LiteLLM stayed active.
- The retained pre-repair trace `8b9b539d...` proves why AR-276 was required: failed preflight still started native `task-general`, made 58 tool calls, and timed out. The new 154 focused, 65 affected, 828 spine, 134 UI, docs, ruff, routing, and diff checks are green.
- Owner-authorized LiteLLM control-plane updates changed only deployment `task-agency-router`; raw DB-row hashes prove 0 unrelated changes across 103 deployments. The alias moved from configured target `ollama/qwen3.5:2b` to `ollama/qwen3.5:9b`, then to `ollama/qwen3-coder-30b-a3b-128k-rocm`. Host-native OpenClaw remains `litellm/task-general`.
- The 9B target produced schema-valid stages but was not reliable: traces `23da5198...` and `a4121506...` ended in critic veto and recruiter no-valid-response. With the 30B target, exact required request trace `7a094495-edbc-471d-8c9d-9a557f3c7ac6` was accepted across planner/recruiter/critic, exact profile/provider/alias, and zero fallback. `response.body.model` still repeats the alias; actual answering model is not claimed.
- Fresh native session `ar276-openclaw-nexus-status-20260822-160727`, run/trace `341ec5f5-9343-499f-8a73-d0c6cb08426c`, and Store run `7daf7c70-c87b-4ed7-bf31-3e093bab73b5` retained a new failure: preflight reached `ready`, but OpenClaw injected 0 runtime-context characters, normal `task-general` answered, and `agency_finalize` failed with invented correlation IDs. Store status is `response_invalid`; no Agency header was delivered.
- Installed OpenClaw 2026.7.1-2 requires non-bundled plugins to opt into prompt mutation. Agency registration grants `allowConversationAccess` but omitted `allowPromptInjection`. Expected-red is retained; the minimal registration/rollback/plan repair is green at 46/46 and the focused OpenClaw slice is 127 passed/1 skipped under umask `0077`. Candidate is not installed yet.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 remains live-proven for native finalization and response delivery. Exact-status is deterministic control proof; the subsequent non-control turn now proves Agency harness/profile/alias selection and strict finalization.
- AR-273 now has an accepted exact substantive Agency-only route through the exact LiteLLM profile and alias. Canonical native header/finalization remains open.
- AR-274 expected-red is 2/2 exact failures; repair is 22 passed/1 skipped plus 453 passed/1 skipped, and fresh `healthcheck` header/Store proof now passes. Proportionate final gates remain; no exhaustive workflow was dispatched.
- AR-275 preserves bounded codes without model coupling. AR-276's input gate is installed; the next candidate adds only the OpenClaw prompt-injection permission required to deliver its already-created preflight context.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Finish the clean checkpoint, stop OpenClaw natively, and reinstall Agency only from this candidate so registration sets `plugins.entries.agency-preflight.hooks.allowPromptInjection=true`.
2. Restart OpenClaw and use a completely new session. The failed sessions and prompts remain immutable evidence and must not be retried unchanged.
3. Require a real five-line header and Store-backed finalization before any Telegram success claim. Hermes remains untouched break glass.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Commit this prompt-injection permission repair and its ledger row.
2. Stop OpenClaw, reinstall Agency only, restart natively, and confirm the permission plus plugin runtime inventory.
3. Run a fresh exact-status session, then a genuinely new substantive turn only after header/Store proof. Keep Hermes and all proven hosts untouched.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

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

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Never expose credential values. Preserve hashes, environment-variable names, and populated booleans only.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change and no Codex canary belongs in this Linux package.
