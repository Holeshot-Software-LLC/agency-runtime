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
evidence_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
minimum_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Branch `codex/ar278-openclaw-one-pass` contains implementation/ledger pair `e5ae8de1` / `7abf9b13`; `origin/main` is `4a326773`, `f76050d7` is an ancestor, and Agency 0.1.0 imports from this checkout.
- Agency-only install `251c4349-f7e3-4640-980d-055b857c0abe` completed from clean checkout `c0426ab9` while OpenClaw was stopped. Bundle `ba344b92...`, runtime `70239e65...`, and launcher SHA `3090708c...` bind to that checkout; the installer did not restart the host.
- OpenClaw remains audited 2026.7.1-2 on native `litellm/task-general` plus six original fallbacks. Its config changed from SHA `17784e2e...` to `3060c3ee...` only at `meta.lastTouchedAt`; models, providers, channels, and credential indirection are unchanged.
- Native restart is RPC-green. The live gateway loaded Agency and `agency-preflight`; Telegram and Slack are configured, connected, running, and probe-green. `LITELLM_API_KEY` is populated without its value being emitted.
- Agency remains harness-scoped to `linux-task-agency-router`, adapter `litellm`, exact alias/model-group `task-agency-router`, `http://127.0.0.1:4000/v1`, and 120000 ms. The global default remains `agency-default`; Codex/Claude/ZCode have no new harness override.
- Fresh native session `b815780c-23fb-4fdb-8731-aed6d162b769` received exact first message `agency status`. Trace `7f4aa31c-9d93-4199-bac0-b5818cea91de`, run `526c86bd-ddca-4878-93a4-8bd09ca029a6`, routing `d8130eb2-d1fa-478e-84e3-bcff1dc6e0ed`, and terminal `6ce7c157-98fd-4ab7-aabc-d4722e02a43b` completed and delivered through Telegram. Zero Agency receipts correctly keep it a deterministic control-only proof.
- A genuinely changed `tmux` read completed under trace `adff32ff-bbd0-4afd-befd-e5c647ac76fc`; header `Skills loaded: tmux` matches Store row `937189d5-d27c-4fea-8829-91e7995f2252`. Three wrapper receipts used automatically selected OpenClaw profile `linux-task-agency-router`, provider type `litellm`, exact alias/model-group `task-agency-router`, and zero fallback.
- The exact restart-safety review completed in native session `84deda15-df94-4aa8-8ed4-853ecd56ff99` under trace `5ba0b638-9db8-4144-8be0-2d9b17f6b51d`, run `ad2b1238-dd8f-49c9-9b30-2107baf7b499`, routing `b5f22f42-4ddf-4a8b-85ed-8fb56c13e7b1`, and terminal `5eb2e7fa-ff50-4728-b7d2-d6a497ff57b5`. Telegram delivered both response chunks.
- The substantive header names `agency-steward`, `ai-evaluation-engineer`, and `ai-data-remediation-engineer`; no delegation; skill `openclaw-operations`; workforce inference through `task-agency-router`; and inference recruitment. Store skill row `a0b9a4ea-2a0c-441d-ae39-a946ff149c6f` and specialist rows `2762c670...` / `8367ed56...` correlate.
- Its three successful wrapper receipts requested exact alias/model-group `task-agency-router` through provider type `litellm` and profile `linux-task-agency-router`; provider attempts were applied and fallback count is zero. Provider telemetry did not supply the actual answering model, so no actual-model claim is made.
- No resident binding, delegation event, child usage, child scope, or child verification row exists. Native tool evidence is read-only and no mutation or delegation command was detected.
- Final Store online backup SHA `affd8f8e...` has source/backup integrity `ok`, schema 47. Contractors remain 15; Agency config SHA `43367ec9...`, OpenClaw config SHA `3060c3ee...`, and launcher SHA `3090708c...` are unchanged from the install checkpoint.
- Redacted status, skill, and substantive artifacts have SHAs `0524fac4...`, `005630dc...`, and `acf1461b...`; response/transcript SHAs are retained in the verification packet. Earlier failed attempts remain preserved there and are not rewritten as successes.
- Hermes preflight used effective home `/home/holeshot/.hermes-nexus`: v0.20.4, native `litellm/task-general`, five fallbacks, nine enabled plugins, populated `LITELLM_API_KEY`/`LITELLM_BASE_URL`, and Agency unregistered. No credential value or channel/user identifier is retained. Online Store backup SHA `affd8f8e...` has integrity `ok`, schema 47; contractors were 15.
- The first stopped-gateway install failed before staging because Hermes's plugin parent was mode `0775`; artifact SHA `72c3a7ac...` and prepared launcher SHA `7c033c97...` are retained. Config SHA stayed `a984d934...` and the plugin target remained absent.
- Tightening only the plugin directory to `0700` and using process umask `0077` changed the prerequisite. Agency-only retry completed as install `06bd5aa2-c8c3-4321-90b2-e413a142c4a7`, bundle `351a7108...`, runtime `70239e65...`, launcher `7c033c97...`; artifact SHA is `93857d15...`. The installer did not restart Hermes.
- Hermes's native model, provider, five fallbacks, environment-file hash, and nine prior plugins remain unchanged. Its only config semantic delta is enabling `agency-preflight` with tool override false. Native plugin doctor passes import/registration with eight hooks and zero tools.
- The Nexus gateway was restarted through its exact systemd unit and is active/running; OpenClaw remains active.
- Fresh Hermes exact status completed parent activation and a `hermes-agent` skill row, but generic finalization mislabeled the host `mcp`; zero workforce/delegation rows remain.
- Fresh OpenClaw exact status loaded `openclaw-operations`, but finalization rejected its tool-refreshed header after the preflight model was lost; no delivery is claimed. Exact IDs and hashes are in the verification packet.
- Expected-red regressions now pass with bounded OpenClaw model correlation and Store-authoritative finalization host attribution: 232 passed / 6 skipped; not installed.

## completed-evidence

- OpenClaw's prior scoped acceptance evidence remains valid, but its newest tool-using status turn exposed a current final-header regression that must pass after reinstall.
- `task-agency-router` remains confined to Agency workforce inference; OpenClaw's native parent stays `task-general`. No Codex, Claude, ZCode, or Hermes route changed.
- Install provenance, config invariants, credential-name presence, contractor preservation, final Store integrity, and zero fallback are retained.
- This package does not prove Rule 4 native-child delivery and does not move an AR-119 matrix cell.
- Hermes installation, parent activation, header, and skill evidence pass; correct native-host attribution and substantive Agency routing remain pending.

## exact-blocker

Checkpoint and install the regression-first repair into each affected Agency
plugin, then prove changed fresh turns without native model changes.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`; security-sensitive tests need process-local `0077`.
- OpenClaw service is `openclaw-gateway.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- Hermes service is `hermes-gateway-nexus.service`; its plugin parent was safely tightened from `0775` to `0700` after the installer correctly refused the shared-write boundary.
- Never emit credential values or numeric channel/user identifiers. The Store channel session key is retained only by SHA.
- OpenClaw `model_call_ended` proves requested metadata, not the LiteLLM answering model. Never promote an alias into an actual-model claim.
- Do not run unsupported host canaries or reconfigure/re-prove Codex.

## next-bounded-work-package

1. Commit the repair/ledger pair, then reinstall Agency only into OpenClaw and Hermes serially.
2. Prove changed OpenClaw status/tool delivery and Hermes native-host finalization attribution.
3. Run Hermes's exact configuration-drift review through Agency `task-agency-router` with zero fallback.

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
