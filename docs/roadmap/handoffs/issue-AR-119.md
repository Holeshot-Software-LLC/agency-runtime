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
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
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
  - docs/decisions/0165-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0166-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0167-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0168-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/decisions/0170-authorize-finalized-openclaw-child-announcements.md
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
- Hermes Agent v0.20.4 remains at effective
  `$HERMES_HOME=/home/holeshot/.hermes-nexus`; native config, environment,
  service, Agency config, and 59-plugin inventory hashes are unchanged.
  Agency-only install `4e97f5a6...` produced runtime `ecc0b1cb...` and launcher
  `3544cff1...`; `LITELLM_API_KEY` is populated by name only.
- Fresh status `42b23dfd...` / `...:7948cbf5` and substantive
  `78ff9331...` / `...:ada0be68` reached Telegram with Store-backed headers.
  The substantive route used automatic `linux-task-agency-router` / `litellm` /
  exact `task-agency-router`, false fallback flags, and no actual-model claim.
  Backups `d1ab6cfd...` and `bce1a2df...` are `ok`, schema 48, contractors 15.
- The changed Hermes async-child draw is retained as failed. Parent run
  `705cfd21-216b-4476-8339-88e73eebb09c`, trace
  `20260825_075940_bc454f4c:20260825_075940_bc454f4c:372aadb7`, finalized
  `response_invalid` as `8f12869c-2558-468e-8c92-6b27f0381934` at
  `2026-08-25T12:01:18.610917+00:00`, before the child completed.
- Delegation `7333c869-49f5-4416-b4e4-11d80a7e1c9f` / work unit
  `unit-231fa91a8d` ran generic worker `sa-0-1835962e` as
  `hermes-subagent:sa-0-1835962e`. Worker
  `native-child:1d729a3e9c46e7703349c48ff3b0b73709681c20f1183e041adb4043c9f2a10f`
  exited 0 at `2026-08-25T12:02:28.564000+00:00`, but has no validated
  specialist, activation, terminal, delivery, scope, or tool-evidence receipt.
- Child route `9ed701ed-dadd-4c06-b5ee-4b3504504643` is
  `native_child_inference_failure`. Journal
  `/home/holeshot/.hermes-nexus/cache/delegation/live/deleg_d19e55e6/task-0.log`
  (SHA-256 `a8960d530d4655aac924bd6e7c49a1fd410b483d78f8f1460aaf65b54812a06d`)
  preserves the finding at 08:02:28 local and its replacement by Agency's
  unverified-draft block. Parent and finding were both blocked.
- Evidence directory `ar119-hermes-child-failed-k7gu0py9` retains Store backup
  `caeddf05fce08d61be5bc41e0a9d773a4fb4f37d2973cb6b7e12d3ba91cda3ed`
  (`ok`, schema 48), Store projection `78c4adfdb7dca8e7d48b5bddb9e642dfd69135df85853ebdbb0c183ffb38019a`,
  and redacted native transcript `e87bb0270df4eb7806faedccd871ea8b48aeca1e8f8d224f6677cba8df16564e`.
- Notification row 533537 arrived at `2026-08-25T12:02:29.733338+00:00`.
  Separate run `dd27dffd-800e-4a54-b07d-c9a165e1274b` / trace `...:4e4a2bc2`
  stored finding SHA `8ef12d74...`, but finalization `dac1bbe9...` rejected the
  same five missing header fields. Telegram marked only the 151-character block
  response-ready at 08:06:56.849 local; no child send-success/delivery receipt exists.

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

Hermes async native-child correlation/finalization is blocked: execution exits
zero, but parent and finding fail finalization and no terminal/delivery proof
exists. Rule 4 remains unproven; no matrix cell moved. Tracker writes remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- AR-284 records that `model_receipts.attempted_fallbacks` currently contains strict-stage ordinals; prove provider fallback from routing flags and provider identities instead.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Fetch/integrate latest main, add a focused Hermes async-correlation regression,
   and make the smallest general bridge/finalization fix.
2. Reinstall Agency only, then use a fresh session and genuinely changed
   async child request to prove compute terminal and accepted parent return.
   Hermes has no native Telegram post-send hook; do not call this Rule 4 or
   transport delivery.

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
