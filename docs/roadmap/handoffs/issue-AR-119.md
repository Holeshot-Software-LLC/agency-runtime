---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-21
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 0c5b2b2a4d8829345bb97c85ea97d4d45fab3280
minimum_ledger_commit: 8a515e60a6967ec6e93fe2aee426373912cec10f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Dedicated worktree `/home/holeshot/code/agency-runtime-ar119-openclaw-hermes-litellm` remains on `codex/ar119-openclaw-hermes-litellm`, based on fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`; `f76050d7` is an ancestor. Current clean local recovery is substantive `0c5b2b2a` plus ledger `8a515e60`; AR-272 is the only uncheckpointed slice.
- Checkout module identity is this worktree, Agency is `0.1.0`, Store schema is 47, and every command uses `python -m agency_runtime.cli`.
- Pre-mutation SQLite backup `~/.agency-runtime/backups/ar119-openclaw-hermes-20260821T203410Z/agency.db` has integrity `ok` and SHA-256 `4d979b8337b208cba8e223921b362839115fef9eeda641ce071189686d11db66`; pre-install contractor count was zero.
- Agency profile `linux-task-agency-router` uses adapter `litellm`, exact requested alias `task-agency-router`, discovered `/v1` base URL, populated `LITELLM_API_KEY`, and 120000 ms. Only OpenClaw and Hermes harness defaults select it; global, Codex, and Claude routes are unchanged.
- OpenClaw native primary is restored and remains `litellm/task-general`; its provider inventory has 21 models and no host-native `task-agency-router` entry or alias. Hermes remains running and unmodified as the break-glass host.
- AR-265 through AR-268 preserve the stopped-status, numeric package revision, private-parent, and null-error bridge repairs. Their source plus tests are committed at `85ad8d88`; AR-269 and AR-270 preserve open uninstall compatibility defects.
- OpenClaw `2026.7.1-2` installation succeeded from the repaired checkout without restarting the gateway. The exact installed bridge status now returns `error: null` and exit 0, fixing the original preflight outage mechanism.
- OpenClaw restarted with 13 plugins, native `litellm/task-general`, connected Slack, and active Telegram polling. Direct unauthenticated CLI send was deliberately suppressed by the Agency outbound gate and is retained as a control-boundary receipt, not a Telegram availability claim.
- Fresh local session `57f19f38-338d-4d93-9c46-eac7b6a4831a`, trace `4959bd8c-a0bc-4e3d-bcb9-8cbcc1441547`, produced a visible Agency-shaped header but is a failed attempt: run `61254d1f-80ca-48e0-846d-3c43428d0f72` ended `response_invalid`; finalization event `01af794d-fb97-41c5-8920-2a8bfc2a3558` records missing `actual_model_selected`.
- AR-271 captures the cause. OpenClaw puts the requested model on `model_call_ended.event.model` when `ctx.modelId` is absent, and the generated bridge serializer discarded all receipt fields. The executable Node regression failed pre-fix with exit 83 and passes after the bounded event fallback and serializer allowlist repair.
- Only the OpenClaw gateway was stopped while the Agency integration was reinstalled from the changed checkout; the OpenClaw host package was not reinstalled. Bundle digest is `38dadb1a1a14d5f95319dcc401883a54e6415cf9392803e1b81906ceff718107`; launcher runtime digest is `f7741ed6bfde2844a18151fa43f6536761ba1b6a97a35bdc524d770447309a62`; launcher SHA-256 is `bb033f9b4facce1d78b42b246e0087f8ef6862d825ddcc48cad73b74dc4c5608`.
- The Agency receipt-fix install changed zero managed OpenClaw streaming values. Redacted native-config comparison shows only `meta.lastTouchedAt`; model, provider, and authentication settings did not drift. Four exact raw CLI backups created by these installs were removed; redacted copies and hashes remain.
- OpenClaw is running, RPC/config checks pass, Telegram polling and Slack are connected, and no Telegram inbound has yet been observed. Shared LiteLLM cannot import Agency, so requested alias evidence is available but actual answering model may remain unavailable.
- The first post-AR-271 session is retained as failed: session `264a65e9-7462-4ea7-9b40-9b38206f1b35`, trace `94f32f04-3b72-4ffa-8801-953b320e657f`, preserved four `task-general` request receipts but ended `response_invalid` with no Store-backed header. Native plugin inspection reported zero tools and zero MCP servers. AR-272 adds provider-safe native tool `agency_finalize`, backed by canonical `agency.finalize`; its pre-fix regression exited 91 and 65 focused OpenClaw tests now pass. Telemetry reached 22.5 percent, so this bounded Agency-only fix requires a clean substantive/worklog pair before live work resumes. No AR-119 matrix cell moved.

## completed-evidence

- Starting-point identity, online Store backup, redacted host inventories, LiteLLM reachability, credential-name presence, and callback limitation are preserved.
- The original Telegram-blocking exit-2 receipt, rollback, successful Agency integration installs, both failed response-invalid sessions, Store correlations, red regressions, and bounded fixes are all retained.
- The AR-272 generated-plugin regression failed before repair with Node exit 91. Under the required process-local `0022` test umask, 65 focused OpenClaw security, adapter, and installer tests pass; the earlier fixture trust-guard stop is retained and is not reported as product success.
- Codex OAuth, Codex configuration, Claude configuration, and the consumed Codex canary remain untouched.

## exact-blocker

1. Create the required clean substantive/worklog checkpoint for the AR-272 Agency/OpenClaw adapter fix before another live evaluation.
2. Stop the existing gateway, install only the Agency integration with `--agent openclaw`, inspect it, and restart the same gateway without OpenClaw native-config drift.
3. Run a new OpenClaw session whose first text is exact `agency status`; require terminal Store success and a verified model-receipt-backed header.
4. Then obtain the operator Telegram `/new` followed by exact `agency status`, preserving the first response and delivery receipt before any further message.
5. After control proof, load one harmless skill without delegation and run a genuinely new non-mutating restart-safety review. Correlate Store and provider attempts to `linux-task-agency-router` and exact alias `task-agency-router`.
6. Hermes remains the running break-glass host and must not be mutated or restarted in this package.
7. Tracker creation for AR-265 through AR-272 remains unauthorized. AR-269 and AR-270 remain open. The LiteLLM callback import gap remains an explicit actual-model telemetry limit.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022`; production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Create the local AR-272 substantive and ledger checkpoint.
2. Stop the existing OpenClaw gateway, install only the Agency integration with `--agent openclaw`, inspect it, and restart the same gateway; do not reinstall or reconfigure OpenClaw.
3. Run a fresh local exact-status proof, then Telegram exact status, one harmless skill load, and one new non-delegating restart-safety request.
4. Update both capsules, the loop status, verification packet, contractor count, Store integrity, and final evidence bundle. Keep Hermes untouched.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
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
