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
- Hermes v0.20.4 preflight recorded effective home `/home/holeshot/.hermes-nexus`, native `litellm/task-general`, five fallbacks, nine enabled plugins, config SHA `a984d934...`, and 15 contractors. Online Store backup SHA `affd8f8e...` has integrity `ok`, schema 47.
- First install artifact SHA `72c3a7ac...` retained the fail-closed `0775` plugin-parent refusal before staging. After tightening only that parent to `0700` and using umask `0077`, Agency-only install `06bd5aa2-c8c3-4321-90b2-e413a142c4a7` completed; bundle `351a7108...`, runtime `70239e65...`, launcher `7c033c97...`, install artifact `93857d15...`.
- Hermes native model/provider/fallbacks, environment hash, and nine prior plugins remain unchanged. Config SHA `95b87b7f...` reflects only `agency-preflight` enablement with tool override false. Plugin doctor proves eight hooks and zero tools. The installer did not restart Hermes; the exact Nexus service is now active/running after native restart.
- Fresh Hermes status still has the retained `mcp` attribution defect. OpenClaw two-gate repair `3e71247a` / `ff1e9594` installed as `711f3174-88b1-4b9a-948d-a47f316e6744`; native routes stayed exact and Hermes remained active.
- Diagnostic install `2949e798-5500-45c9-956b-4b5a97aa802b` traced differing lifecycle sessions; artifact SHA `0fe6ae7a...`. Repair `c671dd35` / `278705da` installed Agency-only as `97fd0d49-e833-458a-a4b6-fb818761f212`; bundle `97f95751...`, runtime `145ac94d...`, launcher `9adc2a85...`. RPC/Telegram green, zero restarts; Hermes active.
- Repaired `/new` delivered and consumed one authorization. Fresh status session `130e58cd...`, trace `58bce9a1...`, accepted finalization `9d7d7372...`, `openclaw-operations` row `b2d2f4b8...`, and native Telegram outbound pass. Deterministic control correctly has zero Agency model receipts.
- The following exact restart-safety turn is retained as failed run `324dcb7c...`, trace `755985e5...`. Routing `436eaef9...`, two specialist rows, skill row `ef7b8440...`, and three successful wrapper receipts prove automatic OpenClaw selection of `linux-task-agency-router` and exact alias/model-group `task-agency-router`; actual answering model remains unavailable.
- OpenClaw's native `task-general` parent accumulated about 395 KB across 108 distinct read-only tool results and hit its context-overflow guard without authoring a header. Agency terminal `fba6d9db...` correctly closed it `response_invalid`; Telegram queued nothing. Zero resident binding, delegation, worker, or native-child evidence exists. Artifacts `d4e177d8...` / `31f86489...` and transcript `7a6addc6...` preserve the failure.
- The Agency-only native-error repair binds failed `agent_end` to one exact final `isError` payload with a 30-second, one-use, hashed session/run marker and authoritative Store failure receipt; no raw error content persists. All malformed, stale, replayed, wrong-correlation, and bridge-failure cases remain blocked.
- Focused tests pass 251 / 1 intentional skip, repository Ruff/docs/diff gates pass, and independent security review found no blocker. OpenClaw, Hermes, and all host-native configuration remain unmodified during this candidate package.
- Agency-only install `6ede7fad...` from clean checkout `484fe2de` published bundle `6f7e47bd...`, runtime `a3b8894f...`, launcher `0fd98d4d...`, and 12 required hooks including `agent_end`. The installer left OpenClaw stopped; native restart is RPC-green with zero restarts.
- Contractors remain 15; pre/post Store backups are identical at `07dbad1e...`, integrity `ok`, schema 47. OpenClaw's sole config delta is `meta.lastTouchedAt`; native primary/six fallbacks are unchanged. Telegram/Slack are running and Hermes stays active untouched.
- Fresh `/new` acknowledgement delivered through the installed two-gate authorization. Native session `447738d1...` is empty and redacted acknowledgement artifact SHA is `8fea7044...`; exact first status remains pending.
- Earlier status trace `7e7a6318...` retained the proportional-truncation failure: Store recorded `openclaw-operations`, the native header said `none`, terminal `25cf1630...` failed closed, and Telegram queued nothing. Transcript / trace / artifact SHAs `78d096d5...` / `6c9bc3bc...` / `9a9e2a35...` and the expected-red candidate remain preserved.
- Clean repair/ledger `d7187e80` / `456a75b7` installed Agency only as `fa68e6a4...`: runtime `573a6a14...`, launcher `d65af026...`. RPC, 12 hooks, both channels, native routes, Agency config, and untouched active Hermes remained green.
- Fresh session `6360c186...` passed status as run `86f838f0...`, trace `ad834646...`, routing `a67e66ad...`, terminal `d84fc7d8...`, and Telegram-delivered header `agency-steward / none / none / requested execution alias task-general / deterministic`.
- Changed `node-connect` run `25fa081a...`, trace `c1bbbdc7...`, routing `3548700e...`, specialist `8e538079...`, skill row `d02c71ae...`, and terminal `6907ed38...` delivered its exact Store-backed header. Three applied receipts prove automatic OpenClaw selection of `linux-task-agency-router`, LiteLLM, exact alias/model-group `task-agency-router`, zero fallback, and Telegram delivery.
- Changed substantive run `72314429...`, trace `50c11095...`, routing `21b8b545...`, specialist rows `4bb8ce63...` / `1707c674...`, and terminal `803465de...` delivered `agency-steward, section-508-accessibility-specialist, ai-evaluation-engineer / none / none / workforce inference task-agency-router -> linux-task-agency-router/task-agency-router wrapper / inference`.
- Its four provider attempts comprise three applied and one contract-invalid on the same profile; cross-provider fallback is zero. No delegation or native child exists. Actual answering model is unavailable because the LiteLLM callback is absent. Transcript SHA is `93dcbc...`.
- Final Store backup `02a76504...` has integrity `ok`, schema 47; contractors remain 15. Config, runtime `573a6a14...`, launcher `d65af026...`, and protected hosts are unchanged. OpenClaw acceptance passes; Rule 4/delegation is unproven and no matrix cell moved.
- Hermes reinstall preflight `/tmp/ar119-hermes-final-preinstall.Mr95N6` found no active turn (last activity 13 hours earlier), Hermes v0.20.4, effective home `.hermes-nexus`, native `litellm/task-general` plus the exact five unchanged fallbacks, config SHA `95b87b7f...`, environment SHA `792fd43a...`, launcher `7c033c97...`, and runtime `70239e65...`.
- Store pre/post install backup SHA is `02a76504...`, integrity `ok`, schema 47; contractors remain 15. Plugin inventory stayed 59 total / 6 enabled with SHA `a675e845...`. The owning `hermes-gateway-nexus` service was stopped and the gateway was down; systemd recorded a failed unit exit during stop.
- Agency-only install `0a3d141a...` completed without dashboard or restart: bundle `45b76c0e...`, runtime `573a6a14...`, launcher `e65a0784...`. Hermes config/environment and Agency config hashes are unchanged; plugin doctor reports eight hooks and zero tools.
- The same Hermes service restarted active/running with zero restarts and result `success`. Fresh live-session status, corrected attribution, skill, substantive routing, and delivery are pending; the earlier attribution failure remains retained.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The package proves parent routing only, not Rule 4 native-child delivery or a matrix-cell transition.
- Hermes is reinstalled and activated from the current runtime; fresh live evidence remains pending.

## exact-blocker

OpenClaw has no remaining blocker. Hermes needs a fresh session proving corrected attribution, skill, substantive routing, Store correlation, and delivery.

## same-task-continuity

Continue from the clean Hermes reinstall checkpoint into fresh live proof.

## next-bounded-work-package

1. Create one completely fresh Hermes session without changing native routes.
2. Prove status, corrected attribution, skill, exact Agency routing, Store correlation, and delivery.
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
