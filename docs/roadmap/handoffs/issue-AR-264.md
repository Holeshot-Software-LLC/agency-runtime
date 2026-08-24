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
  - docs/roadmap/issue-AR-282-persist-openclaw-child-terminals-after-delivery.md
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
evidence_commit: 933d9f4a5bb3dcade7ad6dc726b0d267f0582cde
minimum_ledger_commit: 84e85a4ca681394416ac3c0a1b23e73e707f32f3
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
- Installed correction/ledger `10ba4c84` / `8a2bf9b7` is rooted at `/home/holeshot/.agency-runtime/evidence/ar281-openclaw-10ba4c84-hSltm1Sn`. Agency-only install `f361ae58...`, bundle `a12bdf34...`, runtime `77e00aa2...`, and launcher `3fc5e135...` restored service/RPC and 12 hooks without host-config mutation.
- OpenClaw semantic config `e42bf218...`, native `task-general`, and six fallbacks stayed unchanged. Hermes config/env/launcher `95b87b7f...` / `792fd43...` / `e65a0784...` remained active/untouched. Contractors are 15/15; before/after Store backups `6aeaaad4...` / `0a65fa88...` are `ok`, schema 47.
- Third draw parent `5529c6cf...` / trace `a5f6f53b...` spawned exactly one child `7d1c9571...`, native run `06fb1c56...`, delegation `79049f17...`, worker `native-child:9ea15e2f...`, and route `native-child-4ef0e65f...`. Telegram delivered the exact inference header and result; OpenClaw's task ledger says `succeeded` / `delivered`.
- Canonical `99f1388a...` and child routing prove automatic `linux-task-agency-router` / `litellm` / exact `task-agency-router`, zero cross-provider fallback, and no actual-model telemetry. Native execution stayed separately on `task-general`.
- Agency finalized the parent but left the delegation and worker open. Isolated Store replay closes the exact row; the live one-shot hook was swallowed by observation-only and failed-persistence paths that incorrectly relied on a duplicate callback.
- Installed correction/ledger `933d9f4a` / `84e85a4c` still relied on a
  post-cleanup child-end callback. Parent run `0191a16c...`, trace
  `29e96603...`, native run `368bcc67...`, and delegation `d6ceb33a...`
  retain the changed failure: OpenClaw delivered the child response, but
  `cleanup: delete` removed the host registry entry before Agency terminalized
  the worker and delegation.
- AR-282's uninstalled schema-48 candidate records the immutable child outcome
  separately from delivery. Only `message_sent(success=true)` atomically marks
  `delivered` and closes lifecycle; explicit failure stays open, and startup
  reconciles only receipt-backed pending/failed rows as interrupted lifecycle
  failures while preserving the observed child outcome. Generic end/stop
  cannot bypass the gate.
- The host has no shared immutable send identifier. One unique active attempt
  must match every supplied target/channel/account/conversation/session/run
  field and the exact response hash; stale, delayed, replayed, or
  ordinary-identical ambiguity fails closed. Focused validation is 294 passed
  with one unrelated skip and independent review is GO; the installed Store
  remains schema 47 and Rule 4/matrix remain unchanged.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The latest draw proves OpenClaw native-child inference, execution, and
  operational Telegram delivery, but not Agency terminalization or Rule 4.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

The schema-48 post-transport candidate is uninstalled and still needs focused
validation, independent review, a clean local checkpoint, and a changed
OpenClaw retest. Rule 4 separately requires an ADR-0156 host-artifact receipt.

## same-task-continuity

Continue from the clean candidate checkpoint into OpenClaw-only live child proof; keep Hermes as break glass until OpenClaw passes.

## next-bounded-work-package

1. Finish focused validation and review, then checkpoint and install only the post-transport terminal-reconciliation fix into natively stopped OpenClaw.
2. Prove a changed child closes parent, delegation, and worker while delivering through Telegram.
3. Then perform the equivalent Agency-only Hermes proof; preserve Rule 4 as unproven.

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
