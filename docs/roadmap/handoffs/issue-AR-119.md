---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-22
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 7fcd828d2a20d85562bee73cbea9f538985107ac
minimum_ledger_commit: 7d0460a317c3f2528ebaceb5284b8020b63aa431
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Durable branch is clean through repair `7fcd828d`, ledger `7d0460a3`, ADR `60c72239`, and ledger `5d6e1207`; fetched `origin/main` is `4a326773`, and `f76050d7` is an ancestor.
- Agency `0.1.0` imports from this checkout. The first install failed pre-mutation because its user-writable virtualenv was not a trusted persistent launcher; the changed `/usr/bin/python3 -m agency_runtime.cli` input imported this checkout and passed without weakening trust.
- Online backup `~/.agency-runtime/backups/ar274-openclaw-preinstall.bHHyj4vX/agency.db` has integrity `ok`, schema 47, 15 active contractors, and SHA-256 `bdf3c4d6bfedf74251319a9c587b0b64815d35b6a74b15c9f2b65aa18cedb5ff`.
- OpenClaw remains audited `2026.7.1-2 (0790d9f)` on native `litellm/task-general`, six fallbacks, and 21 LiteLLM entries. Pre/current config SHAs are `800f2e664781e7c4cb104d07aa65569dcbdc488e4bbcad80df0876160528a04b` and `341edbcb310b4f51600af6c3452da4a2259b30237d779e940eac85a0ba7c2ff2`; only `/meta/lastTouchedAt` changed. OpenClaw itself was not reinstalled.
- Agency-only install `3aac2a46-e638-46d6-812d-d2df2ea3aa0b` completed with bundle `69783cf41a5e68a25b650aaaf2869ca370b1aefa3123d918e612d6910c376f72`. Launcher runtime digest is `6afbaf655371ae1007d3817baebb188f379c10f4b45ff8c8fe0c67503335adcb`; launcher SHA is `f6962d190ee366d44724691fb01204c79bed3217ee615e83da6be7022845eb36`; install-manifest SHA is `c79882349d19e7995eadbfc85d5dc4d930caef55b74e65346f457129b1ff72ec`.
- Agency config hash remains `43367ec9...`. OpenClaw's harness profile uses `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, `LITELLM_API_KEY`, and 120000 ms. The key is present in OpenClaw's declared common environment and absent from the operator shell; the authenticated model inventory advertises the alias. No global or protected-host route changed.
- Hermes stayed active at config hash `a984d934...`; Codex remains `8f375701...`, Claude `27dafb27...`, and the authorized three Codex MCP flags remain disabled. Codex OAuth/model/canary, ZCode, and all other protected configuration remain untouched.
- Installer left OpenClaw stopped. Native restart is RPC-green; `agency-preflight` is enabled, activated, loaded with ten hooks, `agency_finalize`, and zero diagnostics. Slack is connected/probe-green; Telegram is configured/running and probe-green, with its immediate post-restart connected flag still false. Hermes and LiteLLM remained active.
- Fresh exact first-message session `94f92dc5-a0c5-44a7-bfa0-1663d948025e`, trace `e5b43276-ff90-43a7-923e-9956ac278816`, Store run `31a11c4d-7dff-4c6a-a643-ef082cdea36d`, routing `8ea188b5-1eea-4c05-baea-b712852b78f2`, and finalization `30625a68-a8a5-479f-8cae-07396eec05d8` completed. Binding `rmb-38e874cfe5853841a9cfc14ce50ee651` is request-scoped; native `task-general` recorded zero fallback and actual unavailable. This proves control/final delivery, not Agency inference.
- The consumed session `31f52706-f329-4640-a012-c9540e283770` remains retained as the pre-exact-schema 180-second timeout; it was not retried. The approved content-free diagnostic and expected-red/green receipts remain the repair evidence.
- Fresh healthcheck trace `11707056-a490-4cbc-97b6-9a8e621caa79` completed Store run `585f2dce-a867-4b83-9395-4b877718a22e`, routing `132ee9fa-5cb6-409b-9668-dea79014eac2`, specialists `27d8c6f4-f276-4605-a489-1bb848902ee0` and `4c787672-45d4-4ba9-bb99-2c01a4ce2851`, skill row `3dd34973-d2f5-4b38-adcf-51191f374214`, and finalization `47c0a487-916a-42cb-9d97-54ee205a0a7f`. Its exact inventory-authorized `healthcheck` read produced `Skills loaded: healthcheck`; native transcript SHA is `f45506e3...`.
- All three healthcheck inference stages used profile `linux-task-agency-router`, provider type `litellm`, and exact alias/model-group `task-agency-router`; every response was applied, no protected provider appears, and wrapper telemetry supplies no actual model.
- Substantive trace `6affd162-9e8e-41f5-b513-e33a90e7d819` failed strict recruiter validation and remains `preflight_failed`; receipt `f26a4813-006d-4515-a0ea-f2df6873a4f7` and transcript SHA `dda4518a...` are retained. Changed-input trace `f3582f30-7094-43c3-992f-907b2fcac59e` proved the same three LiteLLM stages, routing `f237b728-f6b1-45b5-ad39-30edd9bdf6e7`, two specialist rows, and skill row `30d8f786-0037-48b1-8af5-319973324828`, but the host model omitted `agency_finalize`. Store run `c1a42bbd-f0d3-4eb4-af46-877b95c5b4e8` remains active with no finalization, so its plausible header is not accepted delivery evidence.
- A bounded revision experiment was expected-red then green but rejected before commit because ADR-0120 forbids corrective model passes. The branch returned clean; no safety rule changed. No host canary ran, no Rule-4 claim or matrix cell moved, and Hermes remains untouched break glass.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 remains live-proven for native finalization and response delivery. Exact-status is deterministic control proof; the subsequent non-control turn now proves Agency harness/profile/alias selection and strict finalization.
- AR-273 is live-proven for structured OpenClaw workforce routing through the exact LiteLLM profile and alias. A distinct substantive turn still needs canonical finalization.
- AR-274 expected-red is 2/2 exact failures; repair is 22 passed/1 skipped plus 453 passed/1 skipped, and fresh `healthcheck` header/Store proof now passes. Proportionate final gates remain; no exhaustive workflow was dispatched.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Run the exact requested substantive restart-safety review in a completely fresh session; accept it only if `agency_finalize`, Store finalization, and native text hash correlate.
2. Recheck Telegram connectivity after the fresh turn. Telegram `/new` remains operator-delivery proof.
3. Keep Hermes and all protected hosts untouched; tracker writes remain unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Run one fresh exact substantive work unit and correlate finalization plus LiteLLM routing.
2. Recheck Telegram, protected hashes, Store integrity, and contractor count.
3. Update final evidence records and run proportionate local gates.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_roster_inference_adapter.py tests/test_inference_profiles.py -q -W error
python -m pytest tests/test_installer_registration.py -q -W error
python -m pytest tests/test_config_policy_namespace_runtime.py tests/test_openclaw_streaming_policy.py -q -W error
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Local host/config/store/install/restart/smoke and local commit authority is current. Push, PR, tracker mutation, and hosted Actions are forbidden.
- Never expose credential values. Preserve hashes, environment-variable names, and populated booleans only.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change and no Codex canary belongs in this Linux package.
