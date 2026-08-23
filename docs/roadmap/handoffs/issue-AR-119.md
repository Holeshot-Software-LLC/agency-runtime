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
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar278-openclaw-one-pass
evidence_commit: da184b4fc6170ff1bffcff8d827910e09b848f6a
minimum_ledger_commit: 773d90807ce17378753af834ce93b1882f31de68
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- The active branch is `codex/ar278-openclaw-one-pass`. Clean local pair `da184b4f` / `773d9080` precedes the current two-file fix; `origin/main` is `4a326773`, `f76050d7` remains an ancestor, and Agency 0.1.0 imports from this checkout.
- OpenClaw remains audited 2026.7.1-2 with native primary `litellm/task-general` and six original fallbacks. Agency remains harness-scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, populated `LITELLM_API_KEY`, and 120000 ms. No protected-host route changed.
- Agency-only install `514528d9-e373-4f87-b1c0-9d53edb9401b` installed bundle `07189d93...`, runtime `f0a563d9...`, and launcher SHA `668ff55d...` from this checkout while OpenClaw was natively stopped. The installer did not restart it. Native restart is RPC-green; Telegram and Slack probe green; Agency is loaded with ten hooks, awaited middleware scoped to `openclaw`, no exposed tool, and zero diagnostics.
- OpenClaw config changed only `meta.lastTouchedAt` and `plugins.entries.agency-preflight.enabled`; native models, providers, channels, and credentials are unchanged. Store schema is 47, contractor count is 15, and post-failure read-only integrity is `ok` with live-snapshot SHA `df57b6a3...`.
- A fourth fresh Telegram attempt is retained. The reset acknowledgement was absent, then exact `agency status` was accepted. Three native `task-general` calls returned HTTP 200 and the transcript contains a natural 665-character response, but the turn kernel recorded `no queued reply payloads`. Native transcript SHA is `13300aef...`.
- Store trace `a9afc0e8-c998-4bff-9c9e-6dce27628bb2`, run `24104a10-ad68-43a3-9a79-92603687cd1b`, routing `30f6b37b-610e-4f4c-8fce-593fe4cd6d8f`, and terminal `625e3e8c-e82c-4918-a23e-5c180760676b` correlate. Control routing correctly abstained/deterministic; no specialist, skill, resident binding, or Agency workforce inference was expected.
- The intended five-line response began exactly:

~~~text
Agency/Agencies loaded: agency-steward
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: requested execution alias: task-general
Recruited via: deterministic
~~~

- Finalization failed closed with only `actual_model_selected` missing. OpenClaw's supported hook reported LiteLLM plus requested alias `task-general`, not an answering model. Agency correctly refused to promote the alias, but three alias-only receipts were persisted after the header was authored and changed the authoritative evidence line before final validation.
- Expected-red proof now reproduces that post-authoring evidence mutation. The OpenClaw bridge fix omits only alias-only LiteLLM hook events from actual-model completion evidence; genuine resolved-model receipts remain unchanged. The focused OpenClaw slice passes 31 tests with 1 skip.
- Hermes remains the running break-glass host. Codex OAuth/config/canary, Claude, and ZCode remain untouched. No host canary, child-delivery claim, matrix movement, push, PR, tracker mutation, or hosted workflow occurred.

## completed-evidence

- Starting identity, SQLite online pre-install backup, redacted inventories, credential-name presence, config invariants, install/launcher provenance, and all four failed live turns are retained.
- The awaited middleware worked: native tool results continued, Agency produced the updated Store-backed header, and the model produced one natural final. The remaining failure is causally isolated to alias-only model evidence arriving after response authorship.
- AR-273 still proves exact OpenClaw Agency workforce profile/provider/alias selection on the free target without protected-host fallback. This deterministic status turn does not re-prove workforce inference and does not claim an answering model.
- The new fix changes only Agency's OpenClaw bridge and one focused regression. It does not change shared header policy, another harness, OpenClaw source/configuration, model routing, or the outbound safety gate.

## exact-blocker

1. The two-file alias-only evidence fix is locally green but not checkpointed or installed.
2. Create the required substantive/ledger pair, stop OpenClaw natively, reinstall Agency Runtime only from that clean checkout, and restart OpenClaw natively.
3. Use a genuinely new fresh Telegram status work unit; do not retry the consumed input unchanged. Hermes remains outside this package.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`. Effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Record only credential variable names and populated booleans. Do not expose values or channel/user numeric IDs.
- Do not run unsupported OpenClaw/Hermes host canaries or reconfigure/re-prove Codex.
- OpenClaw's `model_call_ended` hook is sanitized: it proves provider and requested model metadata, not LiteLLM's answering model.

## next-bounded-work-package

1. Run focused/docs/lint checks and create the clean substantive/ledger checkpoint.
2. Reinstall Agency only into natively stopped OpenClaw; verify launcher provenance, config path-only diff, plugin contract, channels, and Store integrity.
3. Ask for a fresh Telegram reset/status attempt, preserve the first host response, then continue to harmless skill and genuinely new substantive proof only if status delivery passes.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_openclaw_adapter.py tests/test_security_turn_boundaries.py -k openclaw -q
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
- Never expose credential values. Preserve hashes, environment-variable names, and populated booleans only.
- Do not weaken executable trust, final-only delivery, Store correlation, inference evidence, or child-delivery checks.
- No Codex OAuth/configuration change and no Codex canary belongs in this Linux package.
