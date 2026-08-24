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
evidence_commit: c7520586143d9a497dce37f32cad994de66ffb00
minimum_ledger_commit: 2bf42059cb1e46fa2e25f2d7847c85b9cf1b9b84
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
- AR-280/AR-281 retain durable parent/child/launch correlation and exact one-use completion finalization on the parent trace, with no synthetic completion run or inference receipt.
- Clean correction/ledger `c7520586` / `2bf42059` was installed from the exact checkout; evidence is `/home/holeshot/.agency-runtime/evidence/ar281-openclaw-c7520586-4ceF3vbq`. Pre-install online backup `736434a7...` and source are `ok`, schema 47. OpenClaw 2026.7.1-2 stopped natively while Hermes stayed active.
- Agency-only/no-dashboard install completed without gateway restart; backup path is `~/.agency-runtime/backups/openclaw/20260824T195320.228690Z`. Bundle `ae5b0a3e...`, runtime `46ed926c...`, install `ed2572b6...`, launcher `46c4fd6e...`; native restart restored service/RPC and 12 loaded/enabled/activated hooks.
- Agency config `43367ec9...` retains only `api_key_env`; process credential presence is true without value access. OpenClaw semantic config `5f806455...`, native `task-general`, and six fallbacks are unchanged; contractors 15/15 and post-install Store `ok`/47. Hermes config/env/launcher `95b87b7f...` / `792fd43a...` / `e65a0784...` remain unchanged; no Hermes install. Config validation's cold-inventory/protected-host/legacy-provider degradation is expected.
- Retained failed-draw `/new` was acknowledged. Parent `a0f349c8...` / trace `856341f9...` spawned native worker `e0ee5df5...` / run `b182db5c...`; the read-only child completed but its completion was blocked before Telegram queueing. Child staffing has one applied OpenClaw `linux-task-agency-router` / `litellm` / exact `task-agency-router` receipt, zero fallback, and no actual-model telemetry.
- Ready-receipt integrity required one total route after valid child inference appended another. The strict correction is independently Critical/High GREEN: focused 113/1, spine 848/3, docs 780/worklog 1155, Ruff 682, UI 134, routing eval, conformance baseline plus 160/160 killed, diff clean. Retained eval-environment failures precede the owner-private `/usr/bin/python3` pass; no exhaustive corpus ran. Installed correction is live-unproven; no fresh draw started. Rule 4/matrix remain unchanged.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The latest draw additionally proves OpenClaw native-child inference and child
  execution, but not completion delivery, Rule 4, or a matrix-cell transition.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

The correction is installed and healthy but awaits a fresh Telegram `/new` and changed child-delivery retest. Rule 4 remains unproven without ADR-0156 host-artifact receipts.

## same-task-continuity

Continue from the clean parent checkpoint into OpenClaw-only live child proof; keep Hermes as break glass.

## next-bounded-work-package

1. Ask the operator for fresh Telegram `/new`, then prove a genuinely changed OpenClaw child turn and delivery.
2. Correlate its Store/provider/routing/delegation/lifecycle and transport receipts.
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
