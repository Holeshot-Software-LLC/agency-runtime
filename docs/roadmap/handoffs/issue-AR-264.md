---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-25
tags: [handoff, contractors, hiring, prompts, workforce]
related:
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
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
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/decisions/0164-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0165-delegate-exact-schema-translation-to-litellm.md
  - docs/decisions/0166-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/decisions/0167-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/decisions/0169-authorize-finalized-openclaw-child-announcements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar278-openclaw-one-pass
evidence_commit: f2c472b5355638ecf720167e60e612b8f772146a
minimum_ledger_commit: a04a1d2fc09257188211c6612cc315d2cabc54c4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Last clean checkpoint is status ledger `a04a1d2f` over
  current `origin/main` `fc077039`. All 15 packaged contractors remain present.
- Historical OpenClaw/Hermes failures remain in the canonical loop and packet;
  this capsule projects only current recovery state.
- Merged schema-48 runtime `5511300e` is installed Agency-only with launcher
  `0ddbe52d...`; that OpenClaw package left its native configuration and Hermes
  untouched. Integrated focused tests pass 781/1, named fast spine 852/3,
  dashboard 134, Ruff 683, and docs.
- Changed parent `c067362a...` / trace `079b9ba8...` loaded `code-reviewer`,
  executed one native `sessions_spawn` worker, and delivered through Telegram.
  Post-send success closed worker `native-child:9b3d120a...` with outcome `ok`
  / delivery `delivered` and delegation `0d9f02a8...` as `completed`.
- Parent and child receipts use only automatic OpenClaw profile
  `linux-task-agency-router`, provider `litellm`, and exact
  `task-agency-router`; fallback is false and actual model unavailable. Fresh
  status `cc936edb...` / `6f57aca7...` also completed and delivered its exact
  deterministic header.
- OpenClaw is deliberately request-scoped: binding `rmb-fef54dcc...` is in the
  ready run recipe and no `resident_manager_bindings` row is expected. The
  Store is schema 48 and live integrity is `ok`.
- Skill trace `3645e474...` delivered `openclaw-operations` with Store row
  `3e57162a...` and no worker. Changed substantive trace `06785961...` delivered
  `code-reviewer` plus the skill, with three same-profile LiteLLM attempts,
  false fallback flags, no child/delegation, and finalization `a6833f9a...`.
- Final SQLite backup `a0d558a3...` is integrity `ok`, schema 48, contractors
  15; native `task-general` plus six fallbacks remains exactly equal to prework.
- Hermes Agent v0.20.4 remains on its unchanged native configuration. Effective
  home is `/home/holeshot/.hermes-nexus`; config `95b87b7f...`, environment
  `792fd43a...`, service `404d3227...`, Agency config `43367ec9...`, and plugin
  inventory `b2f76100...` match pre-install. Credential evidence is only
  `LITELLM_API_KEY` populated; no value is retained.
- Agency-only install `4e97f5a6...` wrote bundle `05bada29...`, runtime
  `ecc0b1cb...`, and launcher SHA-256 `3544cff1...`; contractors stayed 15/15.
  The installer did not restart Hermes. The existing service restarted active
  with result `success` and the same 59-plugin inventory.
- Fresh first-message status run `42b23dfd...`, trace
  `20260825_065425_f0b77171:...:7948cbf5`, route `03143a75...`, and finalization
  `dd660adc...` delivered through Telegram. Exact header:
  `agency-steward / none / hermes-agent / observed host receipt task-general /
  deterministic`. Skill Store row is `6a8cbe40...`; worker/delegation count is 0.
- Request-scoped binding `rmb-c5df89aa...` is in the ready run recipe; zero
  persistent rows is expected. The status route correctly did not attempt
  workforce inference. Native `task-general` receipts are not Agency-router or
  actual-upstream-model proof.
- Redacted transcript artifact `native-transcript-redacted-index.json` has
  SHA-256 `22e13b75...`; response SHA is `243e806c...`. Post-status Store backup
  `d1ab6cfd...` is integrity `ok`, schema 48; contractors remain 15.
- Substantive run `78ff9331...`, trace `...:ada0be68`, accepted route
  `0697fd16...`, specialist `4fec5063...` (`ai-evaluation-engineer`), and
  finalization `83689dc3...` correlate the native Telegram stream-edit and
  response-ready read-only review.
  Six Store skill rows reduce to `hermes-agent`, `pr-review-workflow`, and
  `agent-runtime-operations`; worker/delegation count is zero.
- Three applied stages prove automatic Hermes selection of
  `linux-task-agency-router` / `litellm` / exact alias/model-group
  `task-agency-router`, with false fallback flags. Wrapper/host receipts do not
  supply an authoritative actual upstream model; callback rows are zero.
- Response SHA `14755b59...`, redacted 127-row turn artifact `84b2c327...`, and
  post-substantive Store backup `bce1a2df...` (`ok`, schema 48, contractors 15)
  are retained. The 640.6-second turn completed and delivered without timeout;
  all native and Agency configuration/launcher hashes remain unchanged.
- Internal post-response run `125ba6c2...` / receipt `9bc23ae7...` preserves two
  same-profile contract-invalid planner rejections. Its blank non-user turn
  created no route, receipt, finalization, specialist, skill, worker, or
  delegation and did not alter the finalized response-ready user turn.
- Changed Hermes child run `705cfd21...` / exact trace `...:372aadb7` failed
  finalization `8f12869c...` before delegation `7333c869...` completed. Worker
  `native-child:1d729a3e...` exited 0 at `2026-08-25T12:02:28.564000+00:00`,
  but child route `9ed701ed...` is `native_child_inference_failure` and no
  validated specialist, terminal, delivery, scope, or activation receipt exists.
- Journal `task-0.log` SHA `a8960d53...` preserves the finding and Agency block.
  Post-child run `dd27dffd...` / trace `...:4e4a2bc2` and finalization
  `dac1bbe9...` blocked the finding again; Telegram marked only the block
  response-ready. No child send-success exists and Rule 4 remains unproven.
- Evidence `ar119-hermes-child-failed-k7gu0py9` retains Store backup
  `caeddf05...` (`ok`, schema 48), Store projection `78c4adfd...`, and redacted
  native transcript `e87bb027...`; contractor count remains 15.

## completed-evidence

- OpenClaw reset, activation, exact status, changed skill, substantive inference, first-pass headers, Store correlation, and Telegram delivery pass on the installed repair.
- Install/launcher provenance, contractor preservation, config invariants, final Store integrity, exact alias, and zero fallback are current.
- Native `task-general` and Agency `task-agency-router` remain separate; no actual answering model is invented from wrapper receipts.
- The latest draw proves OpenClaw native-child inference, execution, operational
  Telegram delivery, and post-send Agency terminalization, but not Rule 4.
- Current Hermes install, activation, exact status, status-time skill recording,
  substantive inference, finalization, Store correlation, exact headers, zero
  fallback, and native Telegram stream-edit/response-ready evidence pass.

## exact-blocker

Hermes async-child correlation/finalization is now the scoped blocker. Child
execution completed, but both parent and finding were blocked and no terminal
or delivery proof exists. Rule 4 remains unproven; tracker writes are unauthorized.

## same-task-continuity

Continue from the clean Hermes parent-evidence checkpoint without retesting
unchanged inputs.

## next-bounded-work-package

1. Integrate latest main and add a focused Hermes async-correlation regression
   before the smallest general bridge/finalization fix.
2. Reinstall Agency only; use a fresh, changed async child proof and require
   compute-terminal plus accepted parent-return evidence. Hermes has no native
   Telegram post-send hook; do not claim Rule 4 or transport delivery.

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

- Local Linux host work and local commits are authorized. Push, PR, tracker state, and hosted Actions are not.
- Never expose credential values or channel/user numeric identifiers.
- Do not run unsupported host canaries or move an AR-119 matrix cell.
- Do not touch Codex OAuth/configuration or rerun a Codex canary.
