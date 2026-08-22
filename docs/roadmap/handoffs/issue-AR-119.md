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
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: fba12371f4bf004ffadd9356bb00787b00e6194f
minimum_ledger_commit: 6ad46fb4a1309b3b52396055a73274d2d5d670b9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Dedicated branch `codex/ar119-openclaw-hermes-litellm` is clean at exact-schema repair `fba12371` plus ledger `6ad46fb4`; `f76050d7` is an ancestor.
- Checkout module identity is this worktree, Agency is `0.1.0`, Store schema is 47, and every Agency command used `python -m agency_runtime.cli`.
- Fresh online backup `~/.agency-runtime/backups/ar273-exact-schema-preinstall.TuZp2cjN/agency.db` has integrity `ok`, schema 47, and SHA-256 `731934b20258feacf7d8835a9ba8e32d41844cd5685eef8ca65ad3dc1d51734f`. Installer contractor count stayed 15.
- OpenClaw remains audited `2026.7.1-2 (0790d9f)` on native `litellm/task-general`, six fallbacks, and 21 LiteLLM entries. Pre/current config SHAs are `806404abcff7be7e46875ca8ab5294e582b93d38c55210fb8bc84359c9a14885` and `800f2e664781e7c4cb104d07aa65569dcbdc488e4bbcad80df0876160528a04b`; changed path is only `/meta/lastTouchedAt`. OpenClaw itself was not reinstalled.
- Agency-only install `b526ecdc-a538-4797-a8e8-656ecb3b315b` completed with bundle `94d87723b900387f9dbad0dda73613b449332c34683a4fd68674c0e354314a22`. Runtime digest is `71c917a91ed3527065447e6aa5ec4e36466d1710f7f5d0a41411a5ac585decda`; launcher SHA is `fe71017957b7060d7480fa80b222455b2cc69fe42d2f7b9c71e98ba65573b01b`; manifest SHA is `4760bbee202e904a81e54e8e41723bd52d18840906da409c9d4cb97d26624503`.
- Agency config hash stayed `43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8`. Harness profile `linux-task-agency-router` uses `litellm`, alias `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms; global/Codex/Claude routes are unchanged.
- Hermes stayed active at config hash `a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`. Separately authorized Codex MCP flags `cloudflare-api`, `codegraph_brainlens`, and `robinhood-trading` are false; final Codex hash is `8f375701f072916af504c5ff6bc3d01bd4ec49c2a3ad31477676fbf5f068828b`. Codex OAuth/model/other MCPs, Claude hash `27dafb2742d0da69a49cc8d206fc9cc429feff09cc3738addcf590d9c4358f97`, and ZCode are otherwise untouched.
- Installer left OpenClaw stopped; the same service then restarted gateway/RPC-green. Slack and Telegram are connected/probe-green; `agency-preflight` is enabled, activated, loaded with ten hooks, `agency_finalize`, and zero diagnostics. Hermes and `litellm-gateway` stayed active.
- Fresh exact first-message session `fe3ab39c-fea0-4974-82b2-c85478b10b8a`, trace `3b26c907-2c9d-4240-8160-8c6d7cce6a08`, run `7d9e7bc3-3268-419e-8358-a3ef2ccf93c7`, routing `19de0955-1cb8-40b0-a307-69cf3e001242`, and finalization `97eaacb8-9dcf-4431-8150-0e1d702e8ce3` completed. Response hash `a1d0eba85a66bfa728275ce62f16e0566b7d5be563333ba4fc66303fadcc6ba6` matches transcript SHA `9f37ed86db9cd7ff600955a706c0d0e328ce6e79e85113bb5b8f649b503ba922`. Binding `rmb-1d107f497436b916ad7b32775b1a630d` is correctly non-durable; model receipt `25199eb6-6e9e-4b7b-a2d4-b365a9400053` records native `task-general`, zero fallback, actual unavailable. This proves control/final delivery, not Agency inference.
- Required new substantive session `31f52706-f329-4640-a012-c9540e283770` is retained as an OpenClaw 180-second provider-phase timeout; native transcript SHA-256 is `07257c4875c2526cbb7447be73ff74f2ea7333efd74b67925356dad812a70289`. Agency trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`, run `c080b393-72fd-4133-9485-d3e786e6c90a`, and receipt `de5f98bc-ca21-4b9b-b881-d862bf5b4da8` ended `workforce_provider_unavailable` / `provider_no_valid_response`.
- That one provider attempt automatically selected OpenClaw profile `linux-task-agency-router`, provider `litellm`, and exact alias/model-group `task-agency-router`; fallback count is zero. The OpenClaw process has `LITELLM_API_KEY`, and the local proxy returned HTTP 200 at the attempt boundary. No routing, skill, specialist, finalization, or model row exists. Codex, Claude, and other providers were not attempted.
- The approved one-request diagnostic used the existing credential only in memory and exposed no value or content. HTTP 200 returned a normal envelope and braced JSON, but four keys violated its closed two-key schema. This isolates prompt-only schema enforcement; actual model remains unavailable because the proxy has no Agency callback.
- Expected-red proved LiteLLM still sent `json_object`; repaired payload sends the exact closed `json_schema` while retaining strict validation. The 6/6 repair, 134/134 inference, and 104/104 OpenClaw slices are green and the repair is installed. Alias, target, host inference, proxy, retry, and fallback configuration are unchanged.
- No Telegram-scoped user turn has been submitted after restart. No OpenClaw/Hermes host canary ran, no Rule-4 claim or matrix cell moved, and Hermes remains untouched break glass.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 is live-proven for native finalization and response delivery. Exact-status is deterministic control proof only; the failed skill turn is the first strict evidence of correct Agency harness/profile/alias selection.
- AR-273 has retained red/green evidence for prompt schema, reasoning translation, and exact LiteLLM JSON-schema delivery. The new bundle is installed; fresh live control, skill, and substantive proof remain.
- Focused inference and OpenClaw slices pass 134/134 and 104/104. The earlier full production spine passed 827 with three skips; no exhaustive workflow was dispatched.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Run fresh exact-status, conditional harmless-skill, and genuinely different substantive sessions; correlate Store/provider/header evidence.
2. Do not change the alias, proxy, host-native model, validator, retry, or fallback policy.
3. Telegram `/new` remains operator-delivery proof. Hermes stays active and untouched; tracker writes remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. In fresh sessions, run exact first-message status, conditional harmless-skill proof, then a different non-mutating substantive work unit.
2. Correlate Store/provider/header proof without actual-model invention.
3. Keep Hermes, Claude, ZCode, Codex OAuth/model settings, and OpenClaw native inference untouched.

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
