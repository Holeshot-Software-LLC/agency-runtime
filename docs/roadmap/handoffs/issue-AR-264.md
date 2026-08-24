---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-23
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

- Agency-only install `251c4349-f7e3-4640-980d-055b857c0abe` completed from clean checkout `c0426ab9` with 15 unchanged contractors; bundle `ba344b92...`, runtime `70239e65...`, and launcher `3090708c...` bind to that checkout. The installer left OpenClaw stopped.
- OpenClaw 2026.7.1-2 remains on native `litellm/task-general` plus six unchanged fallbacks. Agency alone is scoped to `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`. The native config changed only its timestamp.
- Fresh exact status in session `b815780c-23fb-4fdb-8731-aed6d162b769` completed trace `7f4aa31c-9d93-4199-bac0-b5818cea91de` and delivered through Telegram. Zero model receipts correctly preserve its deterministic control-only meaning.
- Changed `tmux` trace `adff32ff-bbd0-4afd-befd-e5c647ac76fc` delivered an exact header and matching Store skill row `937189d5-d27c-4fea-8829-91e7995f2252`. Three successful wrapper receipts prove automatic OpenClaw profile selection, LiteLLM, exact `task-agency-router`, and zero fallback.
- Exact substantive restart-safety trace `5ba0b638-9db8-4144-8be0-2d9b17f6b51d` completed run `ad2b1238-dd8f-49c9-9b30-2107baf7b499`, accepted routing `b5f22f42-4ddf-4a8b-85ed-8fb56c13e7b1`, and accepted terminal `5eb2e7fa-ff50-4728-b7d2-d6a497ff57b5`. Telegram delivered both response chunks.
- The substantive header and Store correlate `openclaw-operations` row `a0b9a4ea-2a0c-441d-ae39-a946ff149c6f` plus two specialist rows. Three successful wrapper receipts use `linux-task-agency-router`, `litellm`, exact alias/model-group `task-agency-router`, and zero fallback. Actual answering model remains unavailable.
- No resident binding, delegation, or native-child rows exist. Final Store backup SHA `affd8f8e...` has integrity `ok`, schema 47. Contractors remain 15; Agency config, OpenClaw config, and launcher hashes remain unchanged from the install checkpoint.
- Earlier failed OpenClaw attempts remain retained in the verification packet. Codex OAuth/config/canary, Claude, and ZCode remain untouched.
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

## completed-evidence

- OpenClaw reset, activation, exact status header, skill row, and Telegram delivery pass. Substantive Agency inference now passes, but native completion/header/delivery failed and remains pending.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The package proves parent routing only, not Rule 4 native-child delivery or a matrix-cell transition.
- Hermes install, activation, header, and skill evidence pass; corrected native-host attribution and substantive Agency routing remain pending.

## exact-blocker

Do not retry the terminally failed restart-safety input unchanged. The bounded native-error repair is installed; prove a fresh changed, tightly scoped substantive OpenClaw turn before continuing Hermes.

## same-task-continuity

Continue from the clean Hermes install checkpoint into fresh live evidence.

## next-bounded-work-package

1. Send exact first-message `agency status` in fresh native session `447738d1...`, then prove a changed three-read substantive OpenClaw turn.
2. Correlate Store/provider/header/channel evidence and checkpoint OpenClaw only.
3. Reinstall Hermes only after OpenClaw passes; prove native attribution and exact Agency routing.

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
