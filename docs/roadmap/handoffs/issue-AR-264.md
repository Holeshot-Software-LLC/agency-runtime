---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-24
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
  - docs/roadmap/issue-AR-279-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/decisions/0168-authorize-finalized-openclaw-child-announcements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar278-openclaw-one-pass
evidence_commit: d04d1d6bdd2884b20ed9298a9fb6e8f05c8db257
minimum_ledger_commit: 27e9ec6267522f7ad2d23695737c6a69b9d052f1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six unchanged fallbacks. Agency alone is scoped to `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`. The native config changed only its timestamp.
- Retained Hermes history includes the fail-closed `0775` parent refusal (`72c3a7ac...`), successful private-parent install `06bd5aa2...`, and the original fresh-status `mcp` attribution defect. Native routes remained unchanged.
- Retained OpenClaw failures include context overflow run `324dcb7c...` / terminal `fba6d9db...` with artifacts `d4e177d8...` / `31f86489...` / transcript `7a6addc6...`, and stale-skill trace `7e7a6318...` / terminal `25cf1630...` with evidence `78d096d5...` / `6c9bc3bc...` / `9a9e2a35...`. Both failed closed with no Telegram reply or child/delegation evidence.
- Clean repair/ledger `d7187e80` / `456a75b7` installed Agency only as `fa68e6a4...`: runtime `573a6a14...`, launcher `d65af026...`. RPC, 12 hooks, both channels, native routes, Agency config, and untouched active Hermes remained green.
- Fresh session `6360c186...` passed status as run `86f838f0...`, trace `ad834646...`, routing `a67e66ad...`, terminal `d84fc7d8...`, and Telegram-delivered header `agency-steward / none / none / requested execution alias task-general / deterministic`.
- Changed `node-connect` run `25fa081a...`, trace `c1bbbdc7...`, routing `3548700e...`, specialist `8e538079...`, skill row `d02c71ae...`, and terminal `6907ed38...` delivered its exact Store-backed header. Three applied receipts prove automatic OpenClaw selection of `linux-task-agency-router`, LiteLLM, exact alias/model-group `task-agency-router`, zero fallback, and Telegram delivery.
- Changed substantive run `72314429...`, trace `50c11095...`, routing `21b8b545...`, specialist rows `4bb8ce63...` / `1707c674...`, and terminal `803465de...` delivered `agency-steward, section-508-accessibility-specialist, ai-evaluation-engineer / none / none / workforce inference task-agency-router -> linux-task-agency-router/task-agency-router wrapper / inference`.
- Its four provider attempts comprise three applied and one contract-invalid on the same profile; cross-provider fallback is zero. No delegation or native child exists. Actual answering model is unavailable because the LiteLLM callback is absent. Transcript SHA is `93dcbc...`.
- Final Store backup `02a76504...` has integrity `ok`, schema 47; contractors remain 15. Config, runtime `573a6a14...`, launcher `d65af026...`, and protected hosts are unchanged. OpenClaw acceptance passes; Rule 4/delegation is unproven and no matrix cell moved.
- Hermes v0.20.4 parent acceptance remains retained: Agency-only install `0a3d141a...`, bundle `45b76c0e...`, launcher `e65a0784...`, exact status/skill/substantive Telegram delivery, and same-profile LiteLLM receipts on `linux-task-agency-router` / `task-agency-router` with zero cross-provider fallback. Its final Store backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15.
- The retained first OpenClaw native-child draw executed a real `sessions_spawn` worker and completed its read-only task, but completion was represented by a synthetic `announce:v1:...` run and its targeted send was suppressed before Telegram queueing. The draw also exposed unprojected host timeout and process-local lifecycle correlation; it is failed delivery evidence, not acceptance.
- AR-280/AR-281 project the OpenClaw host-profile timeout, reconcile child lifecycle from durable exact parent/worker/run/launch bindings, and prepare/finalize completion on the parent trace. A single exact implicit-target, one-use message carries the finalized parent header/body; no synthetic completion run or inference receipt is created. Focused validation passes 299 tests with 1 existing skip.
- Clean implementation/ledger `d04d1d6b` / `27e9ec62` is installed through Agency only while OpenClaw 2026.7.1-2 was natively stopped. Bundle/runtime digest `0c2bb3fc...`, launcher `e9169d04...`, native restart, RPC, and all 12 loaded/enabled/activated hooks pass; `LITELLM_API_KEY` is populated in the process without reading its value.
- Native `litellm/task-general` plus six fallbacks and the semantic native config remain unchanged. Contractors are 15 before/after; pre-install Store integrity is `ok`, schema 47. Hermes remained active with config `95b87b7f...`, environment `792fd43a...`, and launcher `e65a0784...` unchanged and received no install/change.
- Fresh Telegram `/new` was acknowledged. Parent `a0f349c8...` / trace `856341f9...` spawned native worker `e0ee5df5...` / run `b182db5c...`; the read-only child completed but its completion was blocked before Telegram queueing. Child staffing has one applied OpenClaw `linux-task-agency-router` / `litellm` / exact `task-agency-router` receipt, zero fallback, and no actual-model telemetry.
- Ready-receipt integrity required one total route after valid `native_child_inference` appended another. The one-canonical-plus-unique-child-route correction is independently Critical/High GREEN after duplicate/timestamp/numeric/JSON/context/route-ID gaps closed. Focused 113/1, spine 848/3, docs 780/worklog 1155, Ruff 682, UI 134, routing eval, decision conformance baseline plus 160/160 killed, and diff check pass. Private-HOME/no-`pytest` and trusted-interpreter failures precede the owner-private `/usr/bin/python3` eval pass; no exhaustive workflow corpus ran. Candidate is locally green but uninstalled/live-unproven; Rule 4 and matrix remain unchanged.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The latest draw additionally proves OpenClaw native-child inference and child
  execution, but not completion delivery, Rule 4, or a matrix-cell transition.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

OpenClaw child execution completes, but the installed build rejects its valid auxiliary route before delivery. The locally green correction awaits checkpoint, Agency-only reinstall, and a changed live retest. Rule 4 remains unproven without ADR-0156 host-artifact receipts.

## same-task-continuity

Continue from the clean parent checkpoint into OpenClaw-only live child proof; keep Hermes as break glass.

## next-bounded-work-package

1. Create the clean correction/ledger checkpoint and reinstall Agency only into stopped OpenClaw.
2. Prove a genuinely changed OpenClaw child turn and Telegram delivery.
3. Touch Hermes only after OpenClaw passes; preserve Rule 4 as unproven.

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

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Never expose credential values or channel/user numeric identifiers.
- Do not run unsupported host canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
