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
  - docs/roadmap/issue-AR-266-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-267-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-268-create-nested-config-parents-privately.md
  - docs/roadmap/issue-AR-269-accept-null-openclaw-control-errors.md
  - docs/roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-272-preserve-openclaw-model-receipt-fields.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-275-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-276-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md
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
  - docs/decisions/0164-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0165-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0166-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0167-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/decisions/0169-authorize-finalized-openclaw-child-announcements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar278-openclaw-one-pass
evidence_commit: 5511300ebc20af31cd6488a009f21f878326c231
minimum_ledger_commit: 7295f28980316739af83ba8fa55c91667022cba1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` installed ledger checkpoint `7295f289`; `origin/main` is `fc077039`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and alias/model-group `task-agency-router`; no protected-host route changed.
- Retained OpenClaw parent acceptance covers fresh status, skill, and substantive
  Telegram responses with exact Store-backed headers. All Agency attempts stayed
  on `linux-task-agency-router` / `litellm` / `task-agency-router` with zero
  cross-provider fallback; actual model telemetry is unavailable.
- Store backup `02a76504...` is `ok`, schema 47, with 15 contractors. Parent
  acceptance passes; Rule 4/delegation remains unproven and the matrix unchanged.
- Hermes v0.20.4 parent acceptance remains retained: Agency-only install `0a3d141a...`, bundle `45b76c0e...`, launcher `e65a0784...`, exact status/skill/substantive Telegram delivery, and Agency LiteLLM receipts on `linux-task-agency-router` / `task-agency-router` with zero cross-provider fallback. Final backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15; actual upstream model is unavailable.
- All native-child failures remain preserved in the canonical loop status and
  packet: suppressed synthetic announcement, open lifecycle after a delivered
  third draw, and `933d9f4a` losing the post-cleanup end callback.
- AR-281/AR-282 retain exact one-use parent-trace completion finalization;
  AR-283 adds the required post-send terminal gate without weakening it.
- Merged schema-48 runtime `5511300e` is installed Agency-only with launcher
  SHA-256 `0ddbe52d...`; OpenClaw's native model configuration is byte-identical
  to the prework backup and Hermes remains untouched. Integrated focused tests
  pass 781/1, the named fast spine 852/3, dashboard 134, Ruff 683, and docs.
- Changed live parent `c067362a...` / trace `079b9ba8...` selected
  `code-reviewer`, spawned one `sessions_spawn` worker, and delivered the exact
  Store-backed result through Telegram. `message_sent(success=true)` recorded
  native outcome `ok`, delivery `delivered`, worker exit 0/end, and delegation
  `0d9f02a8...` `completed`; parent finalization is `c46d714d...`.
- Parent route `fcdb5d39...` has three applied `litellm` attempts and child route
  `native-child-d7bc...` one applied attempt, all on
  `linux-task-agency-router` and exact `task-agency-router`; fallback is false
  and actual-model telemetry remains unavailable. Native execution remains
  separately on `task-general`.
- Fresh status parent `cc936edb...` / trace `6f57aca7...` completed and delivered
  the deterministic five-line header through Telegram. Binding
  `rmb-fef54dcc...` is retained in each ready run recipe as
  `request_scoped` / `request`; zero `resident_manager_bindings` rows is the
  tested OpenClaw contract, not missing evidence.
- The host exposes no shared immutable send ID. One active scope/hash match is
  required; exhaustion, stale/delayed ambiguity, and replays fail closed. The
  installed Store is schema 48 with integrity `ok`.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- All failed draws remain retained. The merged build now proves operational
  parent return, Telegram delivery, and post-send Agency child terminalization.
  Strict ADR-0156 Rule 4 is still unproven; no matrix cell moved.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

The schema-48 OpenClaw child lifecycle passes. Current merged-install acceptance
still needs one harmless no-child skill-load receipt, one new non-delegating
substantive receipt, and the final Store backup/integrity checkpoint. Rule 4
separately requires an ADR-0156 host-authored artifact receipt.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Record a harmless OpenClaw skill load without a child and one changed, non-delegating substantive turn on the installed merged build.
2. Back up the final Store through SQLite, record integrity/hash, and close the OpenClaw evidence bundle.
3. Only then perform the equivalent Agency-only Hermes proof; never promote operational return into Rule 4.

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
