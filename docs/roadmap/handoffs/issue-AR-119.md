---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-24
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
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-279-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
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
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar278-openclaw-one-pass
evidence_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
minimum_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` is based on clean failure-evidence ledger checkpoint `01a8ad24`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected-host route changed.
- Final Agency-only repair `d7187e80` installed as `fa68e6a4...`, runtime `573a6a14...`, launcher `d65af026...`; native routes/hashes stayed unchanged and RPC, 12 hooks, and both channels were green.
- Fresh session `6360c186...` passed exact status (`86f838f0...` / `ad834646...` / `a67e66ad...` / `d84fc7d8...`) and Telegram delivered `agency-steward / none / none / requested execution alias task-general / deterministic`.
- `node-connect` run `25fa081a...`, trace `c1bbbdc7...`, routing `3548700e...`, specialist `8e538079...`, skill `d02c71ae...`, and terminal `6907ed38...` delivered the exact inference header. Three applied receipts prove automatic OpenClaw/LiteLLM profile and exact `task-agency-router` alias/group with zero fallback.
- Substantive run `72314429...`, trace `50c11095...`, routing `21b8b545...`, specialists `4bb8ce63...` / `1707c674...`, and terminal `803465de...` delivered the exact inference header. Three applied plus one contract-invalid attempt stayed on the same profile; zero cross-provider fallback, no child/delegation, actual model unavailable, transcript `93dcbc...`.
- Store backup `02a76504...` is `ok`, schema 47, contractors 15. OpenClaw host-scoped acceptance passes; Rule 4/delegation is unproven and the matrix is unchanged.
- Hermes preflight `/tmp/ar119-hermes-final-preinstall.Mr95N6` found no active turn, v0.20.4, home `.hermes-nexus`, native `litellm/task-general` plus five unchanged fallbacks, unchanged config/environment SHAs `95b87b7f...` / `792fd43a...`, Store `02a76504...` `ok`/schema 47/15 contractors, and stable plugin inventory 59/6 at `a675e845...`.
- The owning service was stopped (systemd retained failed/exit-code), then Agency-only install `0a3d141a...` completed without dashboard/restart: bundle `45b76c0e...`, runtime `573a6a14...`, launcher `e65a0784...`. Doctor passed eight hooks/zero tools; the same service restarted active/running, zero restarts, result `success`.
- Fresh redacted Hermes session `...65697a38` acknowledged reset at 09:58:54. Exact first status run `116caa4a...`, trace `...65697a38:...65697a38:b446051a`, routing `b6ace409...` abstained, terminal `dee42fb2...` completed, and `hermes-agent` row `e6157654...`; Telegram delivered `agency-steward / none / hermes-agent / observed native task-general host receipt / deterministic` (1,140 characters, 223.6 seconds). Response/manifest SHAs are `5b9fd3f2...` / `886d32ac...`.
- Skill run `e328626d...`, trace suffix `432b78d6`, routing `d1da7fd7...`, specialist `b2385c80...`, `codebase-inspection` rows `a070accc...` / `8218bddf...`, and terminal `53a5245b...` delivered `agency-steward, technical-writer / none / codebase-inspection / observed native task-general host receipt / inference`. Three applied same-profile LiteLLM receipts used exact alias/group `task-agency-router`, zero cross-provider fallback; Telegram delivered 427 characters in 58.2 seconds, response SHA `25b5be68...`.
- Exact substantive prompt SHA `d79ece62...` produced run `d29c4652...`, trace suffix `b2e909cf`, routing `1bc084f2...`, `ai-evaluation-engineer` row `b952d046...`, and skill rows `2e62f150...` (`agent-runtime-operations`), `6cac7dc0...` (`pr-review-workflow`), `0bde577c...` (`hermes-agent`). Receipts `72c45dae...` / `5c096da9...` / `6286cc80...` all applied on `linux-task-agency-router` / LiteLLM / exact alias-group, with zero cross-provider fallback; terminal `543adf12...` accepted.
- Telegram delivered the exact substantive header `agency-steward, ai-evaluation-engineer / none / agent-runtime-operations, pr-review-workflow, hermes-agent / native task-general host receipt / inference` and 5,274-character response in 263.9 seconds. Response/manifest SHAs are `1381e301...` / `12637e2a...`; no binding, delegation, worker, activation, or child exists.
- Post-response internal non-user preflights `a9874148...` / `2934adb1...`, `e38ecc07...` / `60547574...`, and `3608e1d2...` / `3f54ebbc...` failed strict planning on the same profile without blocking replies. Bare doctor cwd failure is retained; explicit `hermes plugins doctor agency-preflight --ci` passes eight hooks/zero tools. Config hashes and launcher `e65a0784...` remain unchanged; final backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15. Actual upstream model remains unavailable.
- AR-280 now routes native-child staffing through the owning host profile and uses real OpenClaw/Hermes child identities. Race, durable-receipt, and nested-spawn regressions pass; the consolidated focused gate is 213 passed/1 existing skip and both review scopes are green. No host install or config mutation has occurred for this package yet.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- Earlier failures remain retained; Rule 4 native-child delivery/delegation is unproven and no matrix cell moved.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

Parent acceptance passes. Operational native-child proof is pending one host at a time; strict Rule 4 remains unproven because OpenClaw/Hermes lack ADR-0156 artifact collectors.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Create the required clean implementation/ledger checkpoint.
2. Reinstall Agency only into OpenClaw and prove one fresh native child over Telegram.
3. Only after OpenClaw passes, repeat for Hermes; do not move Rule 4 without an artifact receipt.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and do not retry unchanged code/state.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change or Codex canary belongs in this package.
