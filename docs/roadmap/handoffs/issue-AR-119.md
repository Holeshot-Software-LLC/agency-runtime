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
evidence_commit: 2d7c055a28ec0dea609a88a7229d20a559dfddad
minimum_ledger_commit: a70131d63c511e418edcda2ccae1f8e45866a95a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Dedicated worktree `/home/holeshot/code/agency-runtime-ar119-openclaw-hermes-litellm` is clean on `codex/ar119-openclaw-hermes-litellm`, based on fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`; `f76050d7` is an ancestor. Recovery anchor is substantive `2d7c055a` plus ledger `a70131d6`.
- Checkout module identity is this worktree, Agency is `0.1.0`, Store schema is 47, and every Agency command used `python -m agency_runtime.cli`.
- Latest pre-install online SQLite backup is `~/.agency-runtime/backups/ar272-openclaw-nativehost-preinstall-Ah1yzQNU/agency.db`; live and backup integrity are `ok`, and backup SHA-256 is `64421c3fc50623940930d757f15f7cd5930537ea9f8d9dd682a5ca771c8ea66d`. The bounded install retained 15 contractors before and after.
- OpenClaw remains the existing audited `2026.7.1-2 (0790d9f)` host. Its native primary stayed `litellm/task-general`, fallback count stayed six, provider inventory stayed 21 LiteLLM models / 27 total entries, and Slack plus Telegram channel configuration remained present. Only OpenClaw was stopped and restarted; its package was not reinstalled.
- Agency-only install `479c1a47-7e89-4091-a0f4-548f6913db58` completed with zero contractor changes and no dashboard or gateway restart. Bundle digest is `475e56274dec5f7eb61b54a469489274247caa60a18910ff200ec7757bed59a4`; launcher runtime digest is `52724f5a8803d1662228a67c03c9a986a5eeebc2289ddb68cdad0306272de066`; launcher SHA-256 is `5539744ef47aa464921887ee067e3f3c54c9caeacac252259f5a5bb008d462cb`; install-manifest SHA-256 is `8d25e7420dc7e8614e3981df0b20274d72add6617b7f899112c925287b82e8b6`. The launcher source root is this checkout.
- Redacted native-config comparison shows no model, provider, credential, channel, or plugin-policy drift; only OpenClaw metadata changed. The three generic CLI `.bak` copies created by the bounded install were semantically identical and removed; named historical backups remain.
- Agency configuration hash stayed `43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8`. Profile `linux-task-agency-router` uses adapter `litellm`, exact alias `task-agency-router`, discovered base `http://127.0.0.1:4000/v1`, populated credential variable `LITELLM_API_KEY`, and 120000 ms. Only OpenClaw and Hermes harness defaults select it; the global profile and Codex/Claude routes are unchanged.
- Hermes gateway and dashboard remained active and its config hash stayed `a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`. Codex config hash `11b6765c66fdd463c265a6aaeeb23071a622d819311c3a2f832b7d9cba902aeb` and Claude settings hash `27dafb2742d0da69a49cc8d206fc9cc429feff09cc3738addcf590d9c4358f97` are unchanged. ZCode config remained absent before and after. No protected launcher manifest was created.
- Restarted OpenClaw is native-health green. Slack and Telegram both report configured and running with empty `lastError`. Agency plugin `agency-preflight` is loaded with ten typed hooks, native tool `agency_finalize`, conversation access enabled, zero diagnostics, and zero MCP servers.
- Fresh exact first-message control used session `ba9ea05a-3694-4725-b2ea-0357bd16a112`, trace `c2574ce1-b81b-4e29-b66a-06293c6dde85`, and completed run `aedb79d3-79d9-428c-9eb3-90dbc8aac8c9`. Accepted finalization `b0f9a0f4-8da2-4b54-b678-826b3a5b61bc` is labeled `host=openclaw`; response SHA-256 `bcba81da99187df1157a81e813538251e6108a853b2fb3265a21c9585a3794ca` exactly matches the 680-byte native assistant text in transcript SHA-256 `182788c62ac9dd84cd2c73390f10bbb0e4868826cdb0d9df67bbd7c7b1b980da`.
- Control routing decision `ea8821a5-b220-474b-9713-0fbb1e8d0498` abstained deterministically. Request-scoped binding `rmb-aa818901a43ad2bacee6d93edd010488` is correctly non-durable. Native parent receipts used `task-general` with zero fallback; this proves host control routing, finalization, and delivery, not Agency workforce inference.
- The one harmless skill attempt was retained as failed and not retried: session trace `9384d3a3-0a28-4150-a8fa-ab493efda7bf`, run `a5504721-0aa9-4fa3-98df-f5667c933b5b`, failure receipt `3193483a-712b-4c1d-8f13-ccb6799433a1`, stage `routing`, reason `workforce_inference_failed`. It produced no Store-backed header, finalization, skill row, specialist, routing decision, or model receipt.
- Both planner attempts automatically selected OpenClaw harness profile `linux-task-agency-router`, provider type `litellm`, and exact requested model/model-group `task-agency-router`; both were rejected as `provider_response_contract_invalid`. No Codex, Claude, or other provider fallback occurred. The proxy alias echo is not an actual-model receipt.
- Authenticated proxy metadata maps shared alias `task-agency-router` to `ollama/qwen3.5:2b`, whose model information advertises no function-calling or structured-response support. Strict Agency planner validation therefore remains correctly fail-closed. The shared proxy has no Agency callback; actual answering model remains unavailable.
- No new Telegram-scoped Store run arrived after the local proof. Operator `/new` plus exact `agency status` remains pending. No OpenClaw/Hermes host canary ran, no Rule-4 claim or matrix cell moved, and Hermes remains the untouched break-glass host.

## completed-evidence

- Starting identity, online Store backups, redacted host inventories, credential-name presence, Agency install receipts, launcher provenance, config invariants, and every failed turn are retained.
- AR-272 is live-proven for native finalization and response delivery. Exact-status is deterministic control proof only; the failed skill turn is the first strict evidence of correct Agency harness/profile/alias selection.
- Focused OpenClaw regression and security/adapter/installer slice passes 65/65. The earlier full production spine passed 827 with three skips; no exhaustive workflow was dispatched.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Agency workforce inference cannot pass while shared alias `task-agency-router` resolves to `ollama/qwen3.5:2b` and returns responses rejected by the strict planner contract.
2. Lucas must explicitly authorize remapping that shared alias to a structured-output-capable backend, keeping the requested alias exact, or provide an approved contract-compatible strategy for the existing backend. Do not guess or weaken validation.
3. After that external prerequisite changes, use a fresh non-mutating OpenClaw work unit to prove successful provider-backed routing and then load one harmless skill. Do not retry the consumed input unchanged.
4. Operator Telegram `/new` plus exact `agency status` remains required for channel delivery proof.
5. Hermes remains running and untouched. Tracker writes remain unauthorized, the callback gap remains, and no actual-model or AR-119 matrix claim is available.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022`; production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Wait for explicit authority and an approved structured-output-capable target for the shared `task-agency-router` alias.
2. If authorized, change only that proxy mapping, retain before/after evidence, and run one fresh OpenClaw substantive turn plus skill proof.
3. Correlate operator Telegram exact-status evidence when it arrives. Keep Hermes, Claude, ZCode, Codex, and OpenClaw native inference configuration untouched.

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
