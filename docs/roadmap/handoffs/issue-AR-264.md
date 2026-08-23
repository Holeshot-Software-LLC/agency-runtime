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

## completed-evidence

- OpenClaw installation, activation, final-only delivery, Store-backed skill loading, and exact substantive LiteLLM parent routing now pass.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The package proves parent routing only, not Rule 4 native-child delivery or a matrix-cell transition.
- Hermes installation/registration is current; live activation and routing evidence remain pending.

## exact-blocker

Hermes needs fresh Telegram status, harmless skill, and exact substantive
configuration-drift evidence.

## same-task-continuity

Continue from the clean Hermes install checkpoint into fresh live evidence.

## next-bounded-work-package

1. Send exact first message `agency status` in a fresh Hermes Telegram session.
2. Load one harmless skill without delegation and correlate Store/header evidence.
3. Send the exact configuration-drift review and prove Hermes-scoped `task-agency-router` with zero fallback.

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
