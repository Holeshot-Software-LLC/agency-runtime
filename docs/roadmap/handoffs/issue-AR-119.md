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
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 1b789ac3b66c8e3e3e74e3a16bc66667c07cd517
minimum_ledger_commit: 6d6ea5718aea2698916149467e96fa934adbd457
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Dedicated worktree `/home/holeshot/code/agency-runtime-ar119-openclaw-hermes-litellm` is clean on `codex/ar119-openclaw-hermes-litellm` at AR-273 ledger `6d6ea571`; `f76050d7` is an ancestor.
- Checkout module identity is this worktree, Agency is `0.1.0`, Store schema is 47, and every Agency command used `python -m agency_runtime.cli`.
- Latest pre-install online backup is `~/.agency-runtime/backups/ar273-openclaw-preinstall.egB2rWdT/agency.db`; integrity is `ok`, SHA-256 is `d0098af5056bdc54055f20b1fb3e59f2efdc1111c9abb6215c2b78d8104f1300`, and contractor count stayed 15.
- OpenClaw remains audited `2026.7.1-2 (0790d9f)` on native primary `litellm/task-general`, six fallbacks, and 21 LiteLLM model entries. Exact comparison with pre-install config SHA `d4fb6c53a2fa3675d2ffafe5a2fd18d8b64a8b423c9638a21b018234eed62ef5` finds only `meta.lastTouchedAt`; current SHA is `806404abcff7be7e46875ca8ab5294e582b93d38c55210fb8bc84359c9a14885`. OpenClaw itself was not reinstalled.
- Agency-only install `4dd7ee41-121f-4cde-a391-9cecd0665d72` completed with bundle `51320b45f63cc68db52b267928c1939ab908052f623900a51786228c5b978419`. Launcher runtime digest is `c71fbb41ca8780b5e5a5424ef240dbf92bdf56a36dbc9d2caac70dcfa22d3497`; launcher SHA-256 is `755ec953638d85b175f1b4aa705e9cc388cde3d5011520a6bfc7f2986528a78c`; install-manifest SHA-256 is `dfd5be49fd4354090b97fa49f76aab5abaea17396c2e9f6ea05726d0f0330d8c`.
- Agency config hash stayed `43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8`. Harness profile `linux-task-agency-router` uses `litellm`, alias `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms; global/Codex/Claude routes are unchanged.
- Hermes stayed active at config hash `a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`. Separately authorized Codex MCP flags `cloudflare-api`, `codegraph_brainlens`, and `robinhood-trading` are false; final Codex hash is `8f375701f072916af504c5ff6bc3d01bd4ec49c2a3ad31477676fbf5f068828b`. Codex OAuth/model/other MCPs, Claude hash `27dafb2742d0da69a49cc8d206fc9cc429feff09cc3738addcf590d9c4358f97`, and ZCode are otherwise untouched.
- Restarted OpenClaw is gateway/RPC health-green. Slack and Telegram are configured, running, connected, and probe-green; `agency-preflight` is activated with ten hooks, `agency_finalize`, and zero diagnostics. Hermes gateway/dashboard remain active.
- Fresh exact first-message control session `b610efe7-4e71-43c7-8011-fb13f2736f2b`, trace `de166bdc-d649-462d-996b-b2b030a34a8e`, run `c5e8d0bd-99b5-431c-9bb3-6bead5d2eeef`, routing decision `bf93dd03-9d01-4043-a779-49ddee0adff8`, and finalization `cbc9107f-a34a-4fad-b919-17f3e1ae1d44` completed. Store response hash is `1baaf852ced654e3b5a499153716ae3125c4c07b84756adc6c2b1cf64f7d6b95`; native transcript SHA-256 is `2eeec604f55265e6c245944c2b7fa840c530efc50abb4ea37ac3cdab889049a3`. Request-scoped binding `rmb-5ccde2d9de6ac9c0ca8f254cb45e9a85` is correctly non-durable; native `task-general` receipt `002926dd-b041-40c5-9947-14b37f7b4687` records zero fallback and unavailable actual model. This proves status control/final delivery, not Agency inference.
- Required new substantive session `31f52706-f329-4640-a012-c9540e283770` is retained as an OpenClaw 180-second provider-phase timeout; native transcript SHA-256 is `07257c4875c2526cbb7447be73ff74f2ea7333efd74b67925356dad812a70289`. Agency trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`, run `c080b393-72fd-4133-9485-d3e786e6c90a`, and receipt `de5f98bc-ca21-4b9b-b881-d862bf5b4da8` ended `workforce_provider_unavailable` / `provider_no_valid_response`.
- That one provider attempt automatically selected OpenClaw profile `linux-task-agency-router`, provider `litellm`, and exact alias/model-group `task-agency-router`; fallback count is zero. The OpenClaw process has `LITELLM_API_KEY`, and the local proxy returned HTTP 200 at the attempt boundary. No routing, skill, specialist, finalization, or model row exists. Codex, Claude, and other providers were not attempted.
- The proxy has no Agency callback and no explicit message-logging setting, so actual answering model remains unavailable. A content-free direct response-shape diagnostic is waiting for explicit permission to reuse the existing OpenClaw credential in memory; the rejected attempt made no request and exposed no value. No input is retried unchanged.
- No Telegram-scoped user turn has been submitted after restart. No OpenClaw/Hermes host canary ran, no Rule-4 claim or matrix cell moved, and Hermes remains untouched break glass.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 is live-proven for native finalization and response delivery. Exact-status is deterministic control proof only; the failed skill turn is the first strict evidence of correct Agency harness/profile/alias selection.
- AR-273 has red-before/green-after local evidence for schema delivery/reasoning translation and is installed. The post-repair live provider still lacks a valid response; acceptance remains open.
- Focused OpenClaw regression and security/adapter/installer slice passes 65/65. The earlier full production spine passed 827 with three skips; no exhaustive workflow was dispatched.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Do not change the shared alias, proxy, host-native model, validator, or fallback policy. Preserve the completed control and failed substantive receipts.
2. Exact response-shape classification requires either owner approval for one local in-memory credential use or a separately tested content-free Agency diagnostic. Do not bypass the credential boundary.
3. After classification, add a focused red test for the precise defect, make the smallest general repair, reinstall only Agency into OpenClaw, and use a genuinely different work unit.
4. Telegram `/new` plus exact `agency status` remains an operator-delivery proof. Hermes stays active and untouched; tracker writes remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. With explicit approval, run one bounded local LiteLLM response-shape diagnostic that emits no content or credential; otherwise implement and test equivalent content-free Agency diagnostics.
2. Diagnose the exact 200-response parse failure before any repair or new live unit. Keep all prior attempts consumed.
3. Reinstall only a tested Agency repair, then run a different non-mutating work unit and conditional harmless-skill proof. Keep Hermes, Claude, ZCode, Codex OAuth/model settings, and OpenClaw native inference untouched.

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
