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
  - docs/roadmap/issue-AR-282-persist-openclaw-child-terminals-after-delivery.md
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
evidence_commit: 933d9f4a5bb3dcade7ad6dc726b0d267f0582cde
minimum_ledger_commit: 84e85a4ca681394416ac3c0a1b23e73e707f32f3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` installed ledger checkpoint `84e85a4c`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six unchanged fallbacks. Agency alone uses `linux-task-agency-router`, provider type `litellm`, and alias/model-group `task-agency-router`; no protected-host route changed.
- Retained OpenClaw parent acceptance covers fresh status, skill, and substantive
  Telegram responses with exact Store-backed headers. All Agency attempts stayed
  on `linux-task-agency-router` / `litellm` / `task-agency-router` with zero
  cross-provider fallback; actual model telemetry is unavailable.
- Store backup `02a76504...` is `ok`, schema 47, with 15 contractors. Parent
  acceptance passes; Rule 4/delegation remains unproven and the matrix unchanged.
- Hermes v0.20.4 parent acceptance remains retained: Agency-only install `0a3d141a...`, bundle `45b76c0e...`, launcher `e65a0784...`, exact status/skill/substantive Telegram delivery, and Agency LiteLLM receipts on `linux-task-agency-router` / `task-agency-router` with zero cross-provider fallback. Final backup `bdf1a6e6...` is `ok`/`ok`, schema 47, contractors 15; actual upstream model is unavailable.
- The first OpenClaw native-child draw is preserved as a failure: a real `sessions_spawn` child completed its read-only work, but the completion entered a synthetic `announce:v1:...` run and Agency suppressed its targeted send before Telegram queueing. Staffing still used the unprojected timeout and terminal correlation depended on process memory; execution alone does not prove delivery.
- AR-280/AR-281 retain exact durable completion finalization: one implicit-target, one-use send on the parent trace, with no synthetic completion run or inference receipt.
- Installed correction/ledger `10ba4c84` / `8a2bf9b7` is rooted at `/home/holeshot/.agency-runtime/evidence/ar281-openclaw-10ba4c84-hSltm1Sn`. Agency-only install `f361ae58...` used bundle `a12bdf34...`, runtime `77e00aa2...`, and launcher `3fc5e135...`; native restart restored service/RPC and 12 Agency hooks.
- OpenClaw semantic config `e42bf218...`, native `task-general`, and six fallbacks stayed unchanged. Hermes config/env/launcher `95b87b7f...` / `792fd43...` / `e65a0784...` stayed active and untouched. Contractors are 15/15; pre/post Store backups `6aeaaad4...` / `0a65fa88...` are `ok`, schema 47. Credential presence was checked by environment-variable name only.
- Third changed draw parent `5529c6cf...` / trace `a5f6f53b...` spawned exactly one child `7d1c9571...`, native run `06fb1c56...`, delegation `79049f17...`, worker `native-child:9ea15e2f...`, and route `native-child-4ef0e65f...`. Telegram delivered the exact inference header and one-sentence result; OpenClaw's task ledger says `succeeded` / `delivered`.
- Both canonical route `99f1388a...` and child route used automatic OpenClaw profile `linux-task-agency-router`, `litellm`, and exact alias/model-group `task-agency-router`; cross-provider fallback is zero, actual model unavailable, and native parent/child execution stayed separately on `task-general`.
- Agency finalized the parent but left the delegation `delegated` and worker open. Isolated Store replay closes the exact row, proving the live one-shot hook was swallowed: an observation-only end skipped durable reconciliation, and failed trace-bound persistence relied on a duplicate hook OpenClaw does not guarantee.
- Installed correction/ledger `933d9f4a` / `84e85a4c` still relied on a
  post-cleanup child-end callback. Parent run `0191a16c...`, trace
  `29e96603...`, native run `368bcc67...`, and delegation `d6ceb33a...`
  retain the changed failure: OpenClaw delivered the child response, but
  `cleanup: delete` removed the host registry entry before Agency closed the
  worker and delegation.
- AR-282's uninstalled schema-48 candidate persists the immutable child outcome
  as delivery `pending`; only OpenClaw 2026.7.1-2's post-adapter
  `message_sent(success=true)` atomically marks it `delivered` and closes
  lifecycle. Explicit failure remains open. `gateway_start` reconciles only
  receipt-backed pending/failed rows as interrupted lifecycle failures while
  preserving the observed execution outcome, and generic end/stop handling
  cannot bypass the gate.
- The host exposes no shared immutable send ID. Correlation requires one active
  ledger match across every supplied delivery scope and finalized response
  hash. Active attempts remain at least one hour and consumed tombstones 24
  hours; exhaustion, stale/delayed identical callbacks, and replays fail
  closed. Validation is 294 passed with one unrelated skip; review is GO and
  the installed Store remains schema 47.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- All failed draws remain retained. The latest proves operational parent return
  and Telegram delivery, but Agency child terminalization is still unproven on
  the installed build. Strict ADR-0156 Rule 4 is unproven; no matrix cell moved.
- Hermes reinstall, exact status, corrected attribution, skill, substantive routing, Store correlation, headers, and Telegram delivery pass.

## exact-blocker

The schema-48 post-transport candidate is uninstalled and still needs focused
validation, independent review, a clean local checkpoint, and a changed
OpenClaw child retest. Rule 4 separately requires an ADR-0156 artifact receipt.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Finish focused validation and review, then checkpoint and install only the post-transport terminal-reconciliation fix into natively stopped OpenClaw.
2. Restart natively and prove a changed child closes parent, delegation, and worker while delivering through Telegram.
3. After OpenClaw passes, perform the equivalent Agency-only Hermes proof; never promote operational return into Rule 4.

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
