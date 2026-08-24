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
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
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
  - docs/decisions/0168-authorize-finalized-openclaw-child-announcements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar278-openclaw-one-pass
evidence_commit: d04d1d6bdd2884b20ed9298a9fb6e8f05c8db257
minimum_ledger_commit: 27e9ec6267522f7ad2d23695737c6a69b9d052f1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` is based on clean failure-evidence ledger checkpoint `01a8ad24`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; no protected-host route changed.
- Retained parent repair `d7187e80` installed as `fa68e6a4...`, runtime `573a6a14...`, launcher `d65af026...`; native routes/hashes stayed unchanged and RPC, 12 hooks, and both channels were green.
- Fresh session `6360c186...` passed exact status (`86f838f0...` / `ad834646...` / `a67e66ad...` / `d84fc7d8...`) and Telegram delivered `agency-steward / none / none / requested execution alias task-general / deterministic`.
- `node-connect` run `25fa081a...`, trace `c1bbbdc7...`, routing `3548700e...`, specialist `8e538079...`, skill `d02c71ae...`, and terminal `6907ed38...` delivered the exact inference header. Three applied receipts prove automatic OpenClaw/LiteLLM profile and exact `task-agency-router` alias/group with zero fallback.
- Substantive run `72314429...`, trace `50c11095...`, routing `21b8b545...`, specialists `4bb8ce63...` / `1707c674...`, and terminal `803465de...` delivered the exact inference header. Three applied plus one contract-invalid attempt stayed on the same profile; zero cross-provider fallback, no child/delegation, actual model unavailable, transcript `93dcbc...`.
- Store backup `02a76504...` is `ok`, schema 47, contractors 15. OpenClaw host-scoped acceptance passes; Rule 4/delegation is unproven and the matrix is unchanged.
- Hermes v0.20.4 parent acceptance remains retained: Agency-only install `0a3d141a...`, bundle `45b76c0e...`, launcher `e65a0784...`, exact status/skill/substantive Telegram delivery, and Agency LiteLLM receipts on `linux-task-agency-router` / `task-agency-router` with zero cross-provider fallback. Final backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15; actual upstream model is unavailable.
- The first OpenClaw native-child draw is preserved as a failure: a real `sessions_spawn` child completed its read-only work, but the completion entered a synthetic `announce:v1:...` run and Agency suppressed its targeted send before Telegram queueing. Staffing still used the unprojected timeout and terminal correlation depended on process memory; execution alone does not prove delivery.
- AR-280/AR-281 project the OpenClaw host-profile timeout, reconcile lifecycle durably, and prepare/finalize completion against the exact parent trace. Only one exact, implicit-target, one-use `message(action=send)` can carry the finalized parent header/body; no synthetic completion run or inference receipt is created. The focused gate passes 299 tests with 1 existing skip.
- Clean implementation/ledger `d04d1d6b` / `27e9ec62` is now installed through Agency only while OpenClaw 2026.7.1-2 was natively stopped. Bundle/runtime digest `0c2bb3fc...`, launcher `e9169d04...`, native restart, RPC, and loaded/enabled/activated 12-hook plugin all pass. The live process has `LITELLM_API_KEY` populated; its value was not read.
- Native `litellm/task-general` plus six fallbacks and all semantic config leaves remain unchanged; contractors are 15 before/after and pre-install Store integrity is `ok`, schema 47. Hermes stayed active with config `95b87b7f...`, environment `792fd43a...`, and launcher `e65a0784...` unchanged; no Hermes install/change occurred.
- Fresh Telegram `/new` was acknowledged. Parent `a0f349c8...` / trace `856341f9...` / transcript `4ad38fad...` spawned worker `e0ee5df5...` / native run `b182db5c...` / transcript `bf9127d3...`; the read-only child completed, but Agency blocked completion before Telegram queueing and the operator received nothing. One applied child receipt proves OpenClaw selected `linux-task-agency-router` / `litellm` / exact `task-agency-router` with zero fallback and no actual-model telemetry.
- Exact cause: ready-receipt integrity required one total route after valid `native_child_inference` appended another. The strict one-canonical-plus-unique-child-route correction is independently Critical/High GREEN after duplicate/timestamp/numeric/JSON/context/route-ID gaps closed. Focused 113/1, spine 848/3, docs 780/worklog 1155, Ruff 682, UI 134, routing eval, decision conformance baseline plus 160/160 killed, and diff check pass. Private-HOME/no-`pytest` and trusted-interpreter failures precede the owner-private `/usr/bin/python3` eval pass; no exhaustive workflow corpus ran. Candidate is locally green but uninstalled/live-unproven; Rule 4 and protected hosts remain untouched.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- Both failed child-delivery draws remain retained. The latest proves native
  execution and Agency child inference, but not parent return or Telegram
  delivery. Strict ADR-0156 Rule 4 is also unproven; no matrix cell moved.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

OpenClaw child execution completes, but the installed build rejects its valid auxiliary route before delivery. The locally green correction awaits checkpoint, Agency-only reinstall, and a changed live retest. Rule 4 remains unproven because neither host supplies an ADR-0156 artifact receipt.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Create the clean correction/ledger checkpoint and reinstall Agency only into stopped OpenClaw.
2. Prove a genuinely changed OpenClaw native-child turn and Telegram delivery.
3. Touch Hermes only after OpenClaw passes; never promote operational return evidence into Rule 4.

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
