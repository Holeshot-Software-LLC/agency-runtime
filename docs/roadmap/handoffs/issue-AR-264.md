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
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar278-openclaw-one-pass
evidence_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
minimum_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
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
- Hermes reinstall preflight `/tmp/ar119-hermes-final-preinstall.Mr95N6` found no active turn (last activity 13 hours earlier), Hermes v0.20.4, effective home `.hermes-nexus`, native `litellm/task-general` plus the exact five unchanged fallbacks, config SHA `95b87b7f...`, environment SHA `792fd43a...`, launcher `7c033c97...`, and runtime `70239e65...`.
- Store pre/post install backup SHA is `02a76504...`, integrity `ok`, schema 47; contractors remain 15. Plugin inventory stayed 59 total / 6 enabled with SHA `a675e845...`. The owning `hermes-gateway-nexus` service was stopped and the gateway was down; systemd recorded a failed unit exit during stop.
- Agency-only install `0a3d141a...` completed without dashboard or restart: bundle `45b76c0e...`, runtime `573a6a14...`, launcher `e65a0784...`. Hermes config/environment and Agency config hashes are unchanged; plugin doctor reports eight hooks and zero tools.
- The same Hermes service restarted active/running with zero restarts and result `success`.
- Fresh redacted session `...65697a38` acknowledged reset at 09:58:54. First status run `116caa4a...`, exact trace `...65697a38:...65697a38:b446051a`, routing `b6ace409...` abstained, terminal `dee42fb2...` completed, and `hermes-agent` row `e6157654...`; Telegram delivered `agency-steward / none / hermes-agent / observed native task-general host receipt / deterministic` (1,140 characters, 223.6 seconds). Response/manifest SHAs are `5b9fd3f2...` / `886d32ac...`.
- Skill run `e328626d...`, trace suffix `432b78d6`, routing `d1da7fd7...`, specialist `b2385c80...`, `codebase-inspection` rows `a070accc...` / `8218bddf...`, and terminal `53a5245b...` delivered `agency-steward, technical-writer / none / codebase-inspection / observed native task-general host receipt / inference`. Three applied same-profile LiteLLM receipts used exact `task-agency-router` alias/group with zero cross-provider fallback; Telegram delivered 427 characters in 58.2 seconds, response SHA `25b5be68...`.
- Retained typo input missing its leading `R` produced read-only, non-delegating run `dedbed83...`, trace suffix `40284fac`, selected `senior-secops-engineer`, terminal `d010887b...`, and delivered 4,928 characters in 676.1 seconds.
- Exact substantive prompt SHA `d79ece62...` produced run `d29c4652...`, trace suffix `b2e909cf`, routing `1bc084f2...`, specialist row `b952d046...`, and skill rows `2e62f150...` (`agent-runtime-operations`), `6cac7dc0...` (`pr-review-workflow`), `0bde577c...` (`hermes-agent`). Applied receipts `72c45dae...` / `5c096da9...` / `6286cc80...` all used `linux-task-agency-router` / LiteLLM / exact alias-group with zero cross-provider fallback; terminal `543adf12...` accepted.
- Telegram delivered exact header `agency-steward, ai-evaluation-engineer / none / agent-runtime-operations, pr-review-workflow, hermes-agent / native task-general host receipt / inference` and 5,274 characters in 263.9 seconds. Response/manifest SHAs are `1381e301...` / `12637e2a...`; no binding, delegation, worker, activation, or child exists.
- Post-response internal non-user preflights `a9874148...` / `2934adb1...`, `e38ecc07...` / `60547574...`, and `3608e1d2...` / `3f54ebbc...` failed strict planning on the same profile without blocking replies. Bare doctor cwd failure is retained; explicit `hermes plugins doctor agency-preflight --ci` passes eight hooks/zero tools. Config hashes and launcher `e65a0784...` remain unchanged; final backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15. Actual upstream model remains unavailable.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The package proves parent routing only, not Rule 4 native-child delivery or a matrix-cell transition.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

Both host-scoped acceptance sets pass. Actual upstream Hermes model telemetry and post-response internal strict-planner failures remain known limitations; Rule 4/delegation is unproven.

## same-task-continuity

Continue from the clean dual-host acceptance checkpoint into final records.

## next-bounded-work-package

1. Finalize the current evidence records and local commit/ledger pair.
2. Preserve internal-lifecycle planner failures as a follow-up limitation.
3. Do not claim Rule 4 or move the matrix without native-child delivery evidence.

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
