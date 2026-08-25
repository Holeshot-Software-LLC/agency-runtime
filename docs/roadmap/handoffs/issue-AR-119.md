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
evidence_commit: f2c472b5355638ecf720167e60e612b8f772146a
minimum_ledger_commit: a04a1d2fc09257188211c6612cc315d2cabc54c4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Last clean checkpoint is status ledger `a04a1d2f` over
  current `origin/main` `fc077039`; `f76050d7` is an ancestor and Agency 0.1.0
  imports from this checkout. Integrated focused tests pass 781/1, the named
  fast spine 852/3, dashboard 134, Ruff 683, and documentation gates.
- OpenClaw scoped acceptance is closed on the merged schema-48 runtime. Native
  `litellm/task-general` plus six fallbacks is byte-identical to prework; Agency
  alone uses `linux-task-agency-router` / `litellm` / exact
  `task-agency-router`. Actual answering-model telemetry remains unavailable.
- OpenClaw fresh status, skill, substantive, and one native-child draw all
  finalize and reach Telegram. Parent/child attempts stay on the automatic
  `linux-task-agency-router` / `litellm` / exact `task-agency-router` route with
  false fallback flags; post-send success closes the worker/delegation. Final
  backup `a0d558a3...` is integrity `ok`, schema 48, contractors 15.
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
- New substantive run `78ff9331...` / trace `...:ada0be68` / route
  `0697fd16...` selected `ai-evaluation-engineer`, finalized as `83689dc3...`,
  and the native Telegram adapter recorded a successful stream edit and exact
  response ready. Six Store skill rows represent three header names; no child or delegation exists.
- All three workforce stages used automatic Hermes profile
  `linux-task-agency-router`, provider `litellm`, and exact alias/model-group
  `task-agency-router`; both fallback flags are false. Wrapper receipts echo the
  alias, native host receipts name `task-general`, and zero callback rows leave
  the actual upstream model unavailable.
- Response SHA `14755b59...`, redacted artifact `84b2c327...`, and post-turn
  backup `bce1a2df...` (`ok`, schema 48, contractors 15) are retained. Native
  config/environment/service/Agency-config/launcher hashes remain unchanged.
- The 640.6-second native turn is a pass, not a timeout. Internal post-response
  run `125ba6c2...` separately failed two contract-invalid planner responses on
  the same Agency profile; it created no evidence rows and did not affect the
  finalized response-ready user turn.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive Agency inference, first-pass headers, Store correlation, and Telegram delivery all pass on the installed repair.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- All failed draws remain retained. The merged build now proves operational
  parent return, Telegram delivery, and post-send Agency child terminalization.
  Strict ADR-0156 Rule 4 is still unproven; no matrix cell moved.
- Current Hermes install, activation, status-time skill recording, substantive
  inference, finalization, Store correlation, exact headers, zero fallback, and
  native Telegram stream-edit/response-ready evidence pass.

## exact-blocker

No scoped OpenClaw or Hermes parent blocker remains. Hermes still needs the one
operator-requested operational native-child turn plus final backup/records.
Rule 4 remains separately unproven, AR-284 is non-blocking, and tracker writes
remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- AR-284 records that `model_receipts.attempted_fallbacks` currently contains strict-stage ordinals; prove provider fallback from routing flags and provider identities instead.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. In a fresh Hermes session, execute exactly one harmless native child; preserve operational lifecycle/delivery evidence without calling it Rule 4 proof.
2. Take the final Store backup, close records and proportionate gates, and leave Codex, Claude, and ZCode untouched.

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
