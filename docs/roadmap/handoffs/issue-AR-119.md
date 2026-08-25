---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-25
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
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
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
evidence_commit: 9b51aa18c7437422e9a91f55eea86fbb5f52b832
minimum_ledger_commit: 7a012d4772362ed7ba5b3c305cf13501f7f8d591
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` is clean at ledger `7a012d47` over
  current `origin/main` `fc077039`; `f76050d7` is an ancestor and Agency 0.1.0
  imports from this checkout. Integrated focused tests pass 781/1, the named
  fast spine 852/3, dashboard 134, Ruff 683, and documentation gates.
- OpenClaw scoped acceptance is closed on the merged schema-48 runtime. Native
  `litellm/task-general` plus six fallbacks is byte-identical to prework; Agency
  alone uses `linux-task-agency-router` / `litellm` / exact
  `task-agency-router`. Actual answering-model telemetry remains unavailable.
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
- Skill parent `53f6d825...` / trace `3645e474...` delivered the refreshed header
  with `openclaw-operations`, Store row `3e57162a...`, and no child/delegation.
  Changed substantive parent `2b0033c9...` / trace `06785961...` finalized and
  delivered `agency-steward, code-reviewer / none / openclaw-operations /
  task-agency-router wrapper / inference`, again with no child/delegation.
- Both final inferred turns used three applied attempts only on
  `linux-task-agency-router` / `litellm` / exact `task-agency-router`, with both
  routing fallback flags false and no authoritative actual-model telemetry.
  Final SQLite backup `a0d558a3...` is integrity `ok`, schema 48, contractors 15.
- Hermes Agent v0.20.4 was preserved at effective
  `$HERMES_HOME=/home/holeshot/.hermes-nexus`. The native config, environment,
  service unit, Agency config, and 59-plugin inventory hashes are unchanged.
  `LITELLM_API_KEY` is populated by name only. Agency-only install
  `4e97f5a6...` produced bundle `05bada29...`, runtime `ecc0b1cb...`, and
  launcher SHA-256 `3544cff1...`; the installer did not restart the gateway.
- The existing Hermes service restarted active with result `success`. Fresh
  first-message status run `42b23dfd...` / trace
  `20260825_065425_f0b77171:...:7948cbf5` / route `03143a75...` finalized as
  `dd660adc...` and reached Telegram. Its exact header is
  `agency-steward / none / hermes-agent / observed host receipt task-general /
  deterministic`; skill row `6a8cbe40...` exists and no worker/delegation does.
- Binding `rmb-c5df89aa...` is request-scoped in `runs.preflight_result`; zero
  persistent binding rows is expected. The deterministic control route did not
  attempt workforce inference. Its host `task-general` receipts do not prove an
  upstream actual model or the Agency router.
- Redacted native transcript artifact `native-transcript-redacted-index.json`
  has SHA-256 `22e13b75...`; response SHA is `243e806c...`. Post-status Store
  backup `d1ab6cfd...` is integrity `ok`, schema 48; contractors remain 15/15.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- All failed draws remain retained. The merged build now proves operational
  parent return, Telegram delivery, and post-send Agency child terminalization.
  Strict ADR-0156 Rule 4 is still unproven; no matrix cell moved.
- Current Hermes install, activation, fresh status, skill recording,
  finalization, Store correlation, exact header, and Telegram delivery pass.

## exact-blocker

No scoped OpenClaw acceptance blocker remains. Current Hermes still needs one
new non-delegating substantive turn to prove automatic
`linux-task-agency-router` selection and one bounded operational native-child
turn requested by the operator. Rule 4 remains separately unproven, AR-284 is
non-blocking, and tracker writes remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- AR-284 records that `model_receipts.attempted_fallbacks` currently contains strict-stage ordinals; prove provider fallback from routing flags and provider identities instead.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Send the exact new Hermes configuration-drift review with no delegation; correlate the header, LiteLLM route, finalization, and delivery.
2. In a fresh Hermes session, execute exactly one harmless native child; preserve operational lifecycle/delivery evidence without calling it Rule 4 proof.
3. Take the final Store backup, close records and gates, and leave Codex, Claude, and ZCode untouched.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and do not retry unchanged code/state.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check && python scripts/update_policy_availability.py --check && python scripts/update_worklog.py --check && python scripts/verify_docs.py
ruff check agency_runtime tests scripts && ruff format --check agency_runtime tests scripts && git diff --check
~~~

## constraints

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change or Codex canary belongs in this package.
