---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-21
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 4a3267738bb20519500513ea1498fc68f8ea9443
minimum_ledger_commit: 1fd292b016f67429ca51289430974ffb2dd8382f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status section.
This is a recovery map, not evidence that an unproven matrix cell moved.

## checkpoint

- Linux worktree `/home/holeshot/code/agency-runtime-ar119-openclaw-hermes-litellm` is on `codex/ar119-openclaw-hermes-litellm` from fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`; `f76050d7` is an ancestor. The primary checkout was clean and remains untouched.
- Checkout module identity is the worktree `agency_runtime/__init__.py`; Agency is `0.1.0` and Store schema is 47. All Agency commands use `python -m agency_runtime.cli`.
- Before mutation, both hosts were stopped. The live Store was backed up with SQLite backup semantics to `~/.agency-runtime/backups/ar119-openclaw-hermes-20260821T203410Z/agency.db`; live and backup integrity were `ok`, SHA-256 is `4d979b8337b208cba8e223921b362839115fef9eeda641ce071189686d11db66`, and the pre-install contractor count was zero.
- Existing LiteLLM is active at the host-configured `/v1` endpoint. Client authentication uses populated `LITELLM_API_KEY`; authenticated model inventory contains exact alias `task-agency-router`. No secret value was printed or copied into host configuration.
- Agency config adds only harness defaults `openclaw` and `hermes` to profile `linux-task-agency-router` (`litellm`, exact alias, discovered base URL, `LITELLM_API_KEY`, 120000 ms). Global default, bundled routes, Codex, and Claude routes were preserved.
- The shared LiteLLM service cannot import this Agency installation, so its callback was not added or restarted. Requested-alias receipts remain available; actual answering model is a known telemetry limitation unless another provider receipt supplies it.
- Native inference is restored to the pre-work defaults: OpenClaw and Hermes both select `task-general`. No OpenClaw `task-agency-router` model or alias remains. Both hosts retain the populated `LITELLM_API_KEY` indirection rather than re-embedding a credential; this is the only semantic redacted-config delta besides native touch metadata.
- OpenClaw `2026.7.1-2 (0790d9f)` was stopped before installation. Three preserved fail-closed defects produced AR-265 through AR-267: nested stopped JSON on exit 1 was ignored, the stable numeric package revision was treated as prerelease, and nested Agency backup parents inherited `0775` under umask `0002`. Each has a pre-fix failing regression and a bounded repair.
- Focused evidence is green: 45 installer-registration tests, 18 OpenClaw version/live-gateway tests, and 59 configuration-namespace/streaming tests. The original broader registration attempt failed only because the shell umask made pytest temp roots group-writable; the same suite passed under process-local `0022` without weakening trust checks.
- The first OpenClaw install succeeded with bundle digest `7faa371d6f02f4684ef328529d437683e010969baf1b19078ab4cd25fb05bec4`, launcher SHA-256 `e48158abe08425068fa5f83be64f1fd05c248812023497ba973e7d8d3e8362b8`, and runtime digest `6ccbd9ab3a1ce2c160ad96b1a9df257db4ac4a50811bb8def7348da42c487ddc`. Its first Telegram turn was received but blocked before reply queueing.
- AR-268 is the exact outage cause: bridge control returned `ok: true`, `runtime_enabled: true`, and `error: null` but exited 2. A pre-fix regression failed and the one-line truthy-error repair passes with real-error boundaries unchanged.
- OpenClaw was rolled back while stopped. Native plugin removal succeeded, all five retained streaming values were transactionally restored and verified, and the two manually added model entries were removed. AR-269 and AR-270 preserve two write-free Agency uninstall compatibility failures; managed bundle and rollback evidence remain retained.
- Restored OpenClaw now runs `litellm/task-general`, has the original 12-plugin inventory, connects Slack, and starts Telegram polling. A bounded outbound Telegram message has receipt `30023`; an inbound baseline reply is still pending. Hermes gateway/dashboard remain running as the operator's break-glass host and must not be mutated during the OpenClaw package.
- Telemetry reached 33.3 percent before this recovery, so a clean substantive/worklog checkpoint remains required before the next Agency live evaluation. No AR-119 matrix cell moved.

## completed-evidence

- Origin/main preparation, exact checkout identity, schema/version capture, online Store backup, redacted host/config inventories, LiteLLM alias reachability, credential-name presence, and callback import limitation are retained in the active Codex session.
- OpenClaw and Hermes native defaults are restored and schema/CLI validated without touching Codex OAuth, Codex configuration, Claude configuration, or the consumed Codex canary.
- OpenClaw executable, package namespace, and shared local launcher namespace were tightened only enough to satisfy existing cross-account substitution checks. Failed attempts were not repeated unchanged.
- The failed OpenClaw installed stage, Telegram block, native rollback, and successful baseline channel send are preserved. Header delivery, skill persistence, and substantive LiteLLM routing still require a repaired reinstall and fresh-session proof.

## exact-blocker

1. The restored OpenClaw baseline has proven outbound Telegram delivery but still needs one inbound message and queued reply before Agency is reinstalled.
2. Context telemetry requires this repaired source/documentation state to become a clean substantive/worklog pair before the next Agency live evaluation.
3. Reinstallation must not change the OpenClaw model catalog or primary. Current main's plugin registration and final-only streaming enforcement remain mandatory safety controls; do not omit them or weaken evidence/finalization to satisfy a no-native-write interpretation.
4. After reinstall, OpenClaw needs a completely fresh session whose first text is exact `agency status`, then Store correlation, one harmless skill load, and one genuinely new nondelegating substantive request.
5. Hermes remains the operator's running break-glass host and is excluded from this bounded OpenClaw package. Do not mutate or restart it.
6. The LiteLLM callback cannot import Agency, so requested-alias evidence is available but actual answering model may remain unavailable. Tracker creation for AR-265 through AR-270 remains explicitly unauthorized.

## traps (machine-specific; do not rediscover)

- Shell umask is `0002`. Security-sensitive tests that create trusted temp namespaces need a process-local `0022`; production fixes must still work under `0002`.
- OpenClaw service is `openclaw-gateway.service`. Hermes services are `hermes-gateway-nexus.service` and `hermes-dashboard-nexus.service`; effective Hermes home is `/home/holeshot/.hermes-nexus`.
- The shared client credential indirection lives in `~/.config/ai-secrets/common.env`. Record only variable names and populated booleans.
- Do not run `host-canary --execute` for OpenClaw or Hermes. This package cannot prove Rule 4 native-child delivery and must not move a matrix cell.
- Do not reconfigure or re-prove Codex.

## next-bounded-work-package

1. Capture one baseline inbound Telegram reply and complete the clean substantive/worklog checkpoint.
2. Reinstall only OpenClaw from this repaired checkout without modifying its model catalog or primary, then restart natively.
3. Run the fresh OpenClaw control, skill, and substantive turns; correlate Store and provider receipts without delegation.
4. Update the verification packet and loop status with exact evidence. Keep Hermes untouched until a later explicitly resumed package.

## same-task-continuity

Continue in this task after the checkpoint. Preserve every failed receipt and use a genuinely changed input or work unit for any retry.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
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
