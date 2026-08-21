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
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar264-exact-main-smoke-evidence
evidence_commit: f76050d786cda3a4bc545d3d506d8c1687ce3574
minimum_ledger_commit: 1fd292b016f67429ca51289430974ffb2dd8382f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Worktree `C:\Workspaces\Holeshot Software\agency-runtime-ar264-rollout` is on
  `codex/ar264-exact-main-smoke-evidence`, based exactly on merged remote main
  `f76050d7`. The primary checkout and every unrelated worktree are untouched.
- PR #315 merged the package-v1 migration repair with `[skip ci]`; GitHub ran no
  hosted workflow. The exact merge was installed before any host smoke.
- This capsule records bounded installed-host evidence. It does not claim that
  Claude authentication, Codex Desktop lifecycle delivery, ZCode Agency
  staffing, genuine hiring, or AR-119 matrix acceptance passed.

## completed-evidence

- Owner Store backup
  `pre-ar264-f76050d7-20260821T171621.410934Z.db` is 21,999,616 bytes, passes
  SQLite integrity, and has SHA-256
  `9b9936456e90313b76920a4dfd3890c7c44b0243d4a2781592182325aa2bcdaa`.
- Exact-main installation advanced all 15 known package contractors to revision
  1, contract v2, and two-version lineage. TypeScript remains worker
  `54cb1db1-...`, version `contractor-2-6b0d5cae3b65a44d`, with two accepted
  outcomes and 2/3 promotion readiness.
- Installed bundle digests are Claude `2eaa89cc75f8...`, Codex
  `75f6519c74ba...`, and ZCode `2f1bb95ba204...`. Native roots, staged payloads,
  launchers, registration, and configuration are current. OpenClaw and Hermes
  are absent here by explicit deferral.
- The dashboard task survived as an owned, current registration but was stopped
  after reboot. `dashboard service start` restored authenticated health without
  reinstalling or changing config.
- Authenticated dashboard `/api/workforce` and exact-main CLI return the same 31
  contractors at SHA-256 `401e883532e9...`. A bounded host refresh converged in
  two polls; all five host rows match CLI at `003caceee19d...`, and both surfaces
  report master generation 56.
- Provider-free skills verification passes three exact hook cases: Claude
  `Skill`, Codex `skill_view`, and ZCode `Skill` each persist the skill and emit
  it in the updated first-pass header. The real Store has 19 historical
  `skills_loaded` rows, including Codex `openai-docs`. Fresh installed-session
  evidence is still required.
- Codex activation draw session `01a0255a-b6ba-7880-a427-982c4397c8fd`, trace
  `01a0255a-c4b2-7472-8617-6534e9a8fa21`, stopped at
  `workforce_inference_failed`. Planner and recruiter responses were applied;
  no routing decision, specialist, child start, delegation, delivery, skill, or
  final header followed. The isolated host artifact did load `agency-steward`.
- ZCode host session `sess_57b47433-ac40-4dcf-b9c8-ca9ec9784320` exited 0 and
  started generic child `agent_469477bd-183d-4725-9209-541c79802cd4`.
  Agency run `62345127-...`, trace `37bdf697-...`, instead failed its ordinary
  parent planner through expired `claude-subscription`; it made no decision,
  specialist, skill, or delegation row. The child artifacts contain zero
  `[AGENCY INFERENCE TEAM v6]` markers, so this is host-child proof only.
- No failed work unit was retried. No provider route, Option A pin, contractor
  outcome, promotion, rule, or AR-119 matrix cell changed.

## exact-blocker

1. Claude CLI reports `loggedIn=false`; the operator must restore Claude login.
   Do not retry either consumed Claude work unit.
2. The current Codex Desktop task began before the exact installed lifecycle
   could inject its SessionStart snapshot. It cannot gain that header
   retroactively. A completely new task is required; if it still has no header,
   preserve that as the AR-263 Desktop dispatch gap.
3. ZCode's one draw proved its CLI and generic native child, but its ordinary
   Agency parent planner reached `claude-subscription` and failed before the
   separately pinned GLM child judge. Do not broaden Option A into ordinary
   parent routing.
4. A genuine post-AR-261 hire, ZCode plural-card delivery, Codex native child
   proof, and fresh installed skill header remain open. Hosted Actions remain
   forbidden.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. Option A applies only
to each canary's child judge plus the separately authorized Claude
accepted-outcome parent recruiter. Never reinterpret a generic host child as
Agency staffing, and never infer a provider from the parent host.

## next-bounded-work-package

1. Start a completely new Codex Desktop task in this repository. Send exact
   `agency status` first. Preserve the first response and verify that its Agency
   header is present and that any loaded skill is Store-backed; do not invent a
   `none` result if lifecycle evidence is unavailable.
2. If the header appears, perform one provider-free skill load and verify the
   updated `Skills loaded` line plus its Store row. Do not launch a child merely
   to test the header.
3. Operator restores Claude authentication. Recheck it before authorizing one
   genuinely different Claude hiring work unit. Never replay the consumed SAP
   or Erlang units.
4. Only after the Claude parent path is healthy, run one bounded ZCode
   plural-card proof with its existing GLM child-judge pin. Keep ordinary parent
   routing unchanged.
5. Update this capsule and AR-119 status, run proportional local gates, publish
   through a verified-clean PR with `[skip ci]`, then prepare the exact-main
   Linux OpenClaw/Hermes handoff.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_host_hooks.py::test_successful_tool_use_injects_updated_first_pass_header \
  tests/test_host_hooks.py::test_agency_hook_claude_records_real_tool_evidence_from_stdin \
  -q -W error
node --test tests/dashboard_ui.test.mjs
python -m agency_runtime.cli dashboard service status --json
python -m agency_runtime.cli status --json
python -m agency_runtime.cli workforce list --state contractor --limit 100 --json
git diff --check
~~~

The 14-gate repair harness remains green from the exact merged candidate. This
installed-smoke slice additionally passes the three focused skill-hook cases
and authenticated dashboard/CLI comparisons. No exhaustive shard, Linux host,
hosted workflow, or new provider draw followed.

## constraints

- The real Store migration already ran from exact merged main `f76050d7`; do
  not rerun or edit it manually. Preserve the named backup.
- Hosted CI is not authorized or needed for this local gate package. Claude
  authentication requires operator action before its live smoke.
- OpenClaw and Hermes remain explicitly deferred to the later Linux handoff.
- Do not mutate or clean the primary checkout or unrelated worktrees.
- Do not change provider routing, Option A pins, AR-119 matrix cells, or
  previously consumed live evidence.
- Do not carry recruiter-only closest-worker or selection-evaluation prose into
  native child context.
