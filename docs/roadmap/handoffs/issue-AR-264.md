---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [handoff, contractors, hiring, prompts, workforce]
related:
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-265-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-266-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-267-create-nested-config-parents-privately.md
  - docs/roadmap/issue-AR-268-accept-null-openclaw-control-errors.md
  - docs/roadmap/issue-AR-269-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/issue-AR-270-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-271-preserve-openclaw-model-receipt-fields.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar119-openclaw-hermes-litellm
evidence_commit: 4a3267738bb20519500513ea1498fc68f8ea9443
minimum_ledger_commit: 1fd292b016f67429ca51289430974ffb2dd8382f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Current Linux worktree is `/home/holeshot/code/agency-runtime-ar119-openclaw-hermes-litellm` on `codex/ar119-openclaw-hermes-litellm`, based on fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`; repaired AR-264 anchor `f76050d7` is an ancestor.
- Before installation, the Store held zero contractors. SQLite online backup `~/.agency-runtime/backups/ar119-openclaw-hermes-20260821T203410Z/agency.db` and the live Store both passed integrity; backup SHA-256 is `4d979b8337b208cba8e223921b362839115fef9eeda641ce071189686d11db66`.
- Existing LiteLLM client configuration is reused at its discovered `/v1` endpoint with populated credential variable `LITELLM_API_KEY`. Exact alias `task-agency-router` is present in authenticated model inventory.
- Harness-scoped Agency profile `linux-task-agency-router` is the default only for OpenClaw and Hermes. Global routes plus Codex and Claude harness behavior are preserved. The shared LiteLLM service cannot import Agency, so no callback was added and actual-model telemetry may remain unavailable.
- Native host defaults are restored to `task-general`; exact `task-agency-router` remains only in Agency harness profile. Both hosts use the existing `LITELLM_API_KEY` indirection rather than adding or copying credentials.
- OpenClaw stable version is `2026.7.1-2 (0790d9f)`. Installation preserved three distinct fail-closed defects before repair: stopped nested status on expected RPC exit 1 (AR-265), numeric package revision parsing (AR-266), and permissive-umask intermediate config parents (AR-267).
- Each defect has a focused failing-before/passing-after regression. Green focused sets are 45 registration tests, 18 version/live-gateway tests, and 59 config-namespace/streaming tests.
- The first partial install seeded 263 roster entries and 15 packaged contractors. A later install completed with bundle digest `7faa371d6f02f4684ef328529d437683e010969baf1b19078ab4cd25fb05bec4`, but its first Telegram turn was blocked before reply queueing because a valid Agency control receipt with `error: null` exited 2 (AR-268).
- A failing-before regression now covers AR-268; the bounded exit-predicate repair and real-error boundaries pass. The installed plugin was removed while stopped, all five streaming values were restored transactionally, and added native model entries were removed.
- Two write-free rollback defects are preserved as AR-269 and AR-270. The managed bundle, launcher receipt, 15-contractor Store state, and all failure evidence remain retained.
- Baseline OpenClaw is active on `task-general`, Slack is connected, Telegram polling is active, and outbound Telegram message `30023` succeeded. Hermes remains running and untouched as break glass.
- The post-AR-271 local control preserved native model receipts but ended `response_invalid` because the generated Agency plugin exposed no callable finalizer. AR-272 registers native `agency_finalize`, backed by canonical Store finalization; its pre-fix Node regression exited 91 and 65 focused OpenClaw tests pass. Telemetry is 22.5 percent, so a clean checkpoint precedes the Agency integration install and live evaluation.

## completed-evidence

- Required repository bootstrap, backup, config discovery, redacted inventory, credential-name presence, LiteLLM alias reachability, and host-scoped config validation are retained.
- The failed OpenClaw registration, hook block, native rollback, retained 15-contractor roster, and baseline channel recovery are proven. Header delivery, skill loading, substantive parent inference, and native child delivery remain unproven.
- Codex OAuth/configuration and the consumed Codex canary remain untouched. No hosted workflow, push, PR, or tracker mutation ran.

## exact-blocker

1. Create the clean AR-272 substantive/worklog checkpoint before the next live evaluation.
2. Stop the existing OpenClaw gateway, install only the Agency integration with `--agent openclaw`, then restart the same gateway; do not reinstall or reconfigure OpenClaw.
3. Prove exact control/header/skill/substantive Store evidence in a fresh session. Actual model is unclaimable when LiteLLM emits no reconciled receipt; `task-agency-router` is only the requested alias.
4. Keep Hermes running and untouched as break glass during this bounded package.
5. AR-265 through AR-272 tracker creation remains pending explicit outward-write authorization.

## same-task-continuity

After the recovery pair, continue with OpenClaw only. Hermes is a running break-glass host and remains outside this package. Do not retry a consumed prompt or failure receipt unchanged.

## next-bounded-work-package

1. Commit the AR-272 Agency/OpenClaw adapter recovery state plus its worklog-only ledger record.
2. Install only the Agency integration into the stopped OpenClaw gateway from the repaired checkout, preserving the host package, native model catalog, and primary.
3. Complete OpenClaw fresh-session control, skill, substantive routing, and Store/provider correlation.
4. Update exact AR-119/AR-264 evidence and keep Hermes untouched until a later explicitly resumed package.

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

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Preserve all credential values and failed receipts; record only names, presence, hashes, and redacted sources.
- Do not run unsupported OpenClaw/Hermes child canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
