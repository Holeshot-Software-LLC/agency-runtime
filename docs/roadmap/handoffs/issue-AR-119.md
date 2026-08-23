---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-23
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
evidence_commit: 620b8f19f2ccacf686bac0a252b6772ea470dabd
minimum_ledger_commit: 2fd2aede12f4c8f74b780f562a8b2792c9829bf4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Clean pair `b1bd07c6` / `0ca308d6` contains the reset-race repair, third failure evidence, and ledger; `f76050d7` remains an ancestor and Agency 0.1.0 imports from this checkout.
- Agency profile `linux-task-agency-router` remains harness-scoped to OpenClaw, using `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No protected-host route changed.
- Earlier AR-276/AR-277 control, native skill, LiteLLM-routing, first-pass finalization, timeout, and Store-backup evidence remains in the canonical loop status and verification packet. It established audited OpenClaw 2026.7.1-2, free alias target `ollama/qwen3-14b-abliterated`, exact profile/alias routing without fallback, schema 47, 15 contractors, and unchanged native/protected-host configuration; actual backing-model telemetry remains unavailable.
- Clean pair `1ca46cc9` / `320dc7cf` installed that prompt repair as Agency-only install `74b4c0bc...`; native routing and both configs stayed unchanged. Fresh opaque session `80c9c847...`, trace `2eaaf8e9...`, run `27faf92b...`, routing `9528aa21...`, specialists `f7ac8ffb...` / `68d0a65b...`, skill row `0f548ebf...`, and terminal `9b2d4c3a...` produced exact non-silent final text SHA `202f0d58...`, but no Telegram outbound was queued.
- The text terminal conflicted with the canonical payload hash and the gate failed closed. Pair `a8022a92` / `4fab954b` defers that commit and adds exact one-use reset acknowledgement; 386 tests pass, 1 skips, and three unrelated legacy assertions remain red.
- Agency-only install `87b518e8...` completed: bundle `7f94acf0...`, runtime `1816b6ad...`, launcher `c34c66be...`, 15 contractors, no installer restart. Native restart is RPC/channel-green with 11 hooks and zero diagnostics. Agency config is unchanged; OpenClaw has only a timestamp diff and retains `litellm/task-general` plus six fallbacks.
- Third fresh Telegram trace `4552b87d...` completed all three Agency inference stages through `linux-task-agency-router` and exact `task-agency-router`, accepted routing `bbf1d404...`, and loaded `code-reviewer`. Pending finalization `f9138f55...` returned the Store-backed response, but native `task-general` then emitted exact `NO_REPLY`; terminal `9599d181...` correctly closed run `86d3c0a2...` as `response_invalid`. Transcript/trajectory SHAs are `81b54934...` / `38f1e716...`; Telegram queued nothing.
- Native `/reset` bypasses `message_received`; OpenClaw starts `before_reset` from an unawaited transcript-read task, so its acknowledgement can race the hook. Expected-red exit 227 is retained. The candidate uses exact `before_reset` reasons plus a bounded wait only for the two static acknowledgements; replay and invalid reasons stay blocked. The affected OpenClaw suites pass 218.
- Audited OpenClaw 2026.7.1-2 exposes no supported post-model response replacement: `before_agent_finalize` cannot return a payload, exact `NO_REPLY` is normalized away before `reply_payload_sending`, and terminating tools have no public terminal-presentation setter. Direct send, draft rewrite, or a second model pass would violate ADR-0049/ADR-0120 and remain rejected.
- Lucas selected reversible recovery. Agency uninstall dry-run operation `952ff8f6...`, digest `a497a256...`, failed before mutation because installed-copy provenance is not recognized; AR-269 owns it. The stopped gateway then natively disabled only `agency-preflight`. OpenClaw is active/RPC-green, Telegram and Slack probes are green, Agency is registered-disabled, and normalized config hashes prove only timestamp plus the Agency flag changed. Native models and launcher `c34c66be...` are unchanged. Post-disable Store backup is integrity `ok`, SHA `9c193d2e...`.
- Ordinary recovery now passes: exact Telegram request `reply with pong` received exact assistant `pong`. Redacted channel facts show inbound/outbound, role-aware transcript checks pass, and native artifact SHA is `0420d72c...`. This is ordinary-host proof only; no Agency trace/header claim applies while the plugin is disabled.

## completed-evidence

- Starting identity, Store backup, redacted inventories, credential-name presence, install/launcher provenance, invariants, and every failed turn are retained.
- AR-272 remains proven for native finalization; CLI response delivery and exact substantive routing pass. AR-278 now preserves both independent Telegram failures: silent sentinel and full-envelope terminal conflict.
- AR-273 now has fast accepted Agency-only and native skill routing through the exact LiteLLM profile/alias on free 14B; actual backing model telemetry remains unavailable.
- AR-274 expected-red is 2/2 exact failures; repair is 22 passed/1 skipped plus 453 passed/1 skipped, and fresh `healthcheck` header/Store proof now passes. Proportionate final gates remain; no exhaustive workflow was dispatched.
- AR-275 preserves bounded codes without model coupling. AR-276 preflight, native skill proof, and AR-277 first-pass finalization pass; AR-278 channel delivery is the current blocker. No child-delivery or matrix-cell claim moves.
- Codex OAuth/config/canary, Claude, ZCode, and Hermes were untouched.

## exact-blocker

1. Telegram ingress, LiteLLM staffing, native tools, and Store-backed finalizer construction pass; the current native model emits `NO_REPLY` after the tool, and OpenClaw suppresses it before the payload gate.
2. OpenClaw must expose a supported return-direct/terminal-presentation or post-model payload-replacement contract, or Lucas must separately authorize qualifying a host version/source change. Agency cannot repair this by direct send, rewrite, retry, or native configuration change.
3. Ordinary Telegram recovery passes with Agency disabled. Hermes and protected hosts remain untouched.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022` or stricter; the AR-273 focused slice passed with process-local `0077`. Production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Keep Agency disabled until OpenClaw exposes the supported result-delivery seam.
2. Repair AR-269 separately before relying on ownership-bound OpenClaw uninstall.
3. Use a genuinely new Agency work unit only after that prerequisite; keep Hermes untouched.

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
