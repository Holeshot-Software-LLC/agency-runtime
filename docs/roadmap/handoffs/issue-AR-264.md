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
  Codex Desktop lifecycle delivery, completed Claude contractor execution,
  ZCode Agency staffing, or AR-119 matrix acceptance passed.

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
- Before the new hire, authenticated dashboard `/api/workforce` and CLI returned
  the same 31 contractors at `401e883532e9...`; five host rows matched at
  `003caceee19d...` and master generation 56. CLI now returns 32 contractors;
  post-hire dashboard parity was not re-polled.
- Provider-free skills verification passes three exact hook cases: Claude
  `Skill`, Codex `skill_view`, and ZCode `Skill` each persist the skill and emit
  it in the updated first-pass header. The real Store has 19 historical
  `skills_loaded` rows, including Codex `openai-docs`. Fresh installed-session
  evidence is still required.
- Fresh Desktop task `01a02587-1489-7e13-834e-3299ae05fb43` began after the
  install but received no first-response Agency header. Its task and turn IDs
  join to zero Store runs, resident bindings, and skill rows; the hook log did
  not advance past `2026-08-21T17:52:11Z`. The first user turn was the recovery
  prompt rather than exact `agency status`, so the exact prompt control remains
  unrun. No skill was loaded without authoritative activation.
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
- Claude authentication was restored. New session `560e6da4-...`, trace
  `66dca68e-...`, received the exact installed Agency capsule, accepted
  `cobol-cics-vsam-diagnostics-specialist`, and applied standard-risk hiring case
  `35f59955-...`. Active contractor worker `7c7306dc-...` raises the roster to
  32. Native-child inference used `codex-subscription` as pinned.
- Claude's one progress line omitted the required five-line header. Its only
  child `aa0a0207e0caa208d` remained open with no delivery verification or
  conclusion when the fixed 420-second ceiling terminated the host. The run is
  parent/hiring proof, not completed contractor execution.
- Conditional ZCode session `sess_524d8b86-...`, trace `b08d8d79-...`, exited 0
  with generic child `agent_ce74bc0f-...`. Agency's planner applied, but both
  recruiters were contract-invalid `staff_without_safe_team`; no decision or
  card exists and the GLM judge was never reached. All four artifacts contain
  zero Agency markers.
- No failed work unit was retried. No provider route, Option A pin, contractor
  outcome, promotion, rule, or AR-119 matrix cell changed. The applied Claude
  hire is the only workforce mutation in this slice.
- Documentation validation passes 731 files; 8 warning-strict OpenClaw/Hermes
  canary, artifact-reader, and native-child bridge boundary tests pass.

## exact-blocker

1. A post-install Desktop task still dispatched no observable lifecycle hook
   and has no Store binding. Preserve that as AR-263 while keeping the unsent
   exact-status first-prompt control distinct. Do not load a skill or emit a
   fabricated empty header while activation is unavailable.
2. Genuine post-AR-261 hiring is proven, but Claude header compliance, verified
   child delivery, and completed contractor work are not. The COBOL work unit
   is consumed and must not be retried.
3. ZCode plural-card delivery failed before the separately pinned GLM judge
   because both ordinary recruiter responses violated the safe-team contract.
   Preserve the consumed unit and keep routing unchanged.
4. Codex native-child proof and fresh installed skill header remain open.
   Hosted Actions remain forbidden.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. Option A applies only
to each canary's child judge plus the separately authorized Claude
accepted-outcome parent recruiter. Never reinterpret a generic host child as
Agency staffing, and never infer a provider from the parent host.

## next-bounded-work-package

1. Run proportional documentation/local gates and create the recovery/ledger
   pair. Do not run another Windows provider or child draw in this package.
2. Publish only through a verified-clean `[skip ci]` PR, verify zero hosted
   workflows, and leave tracker #313 open because host smoke is incomplete.
3. Hand exact published main to the owner's Linux box through
   `AR-119-openclaw-hermes-verification-packet.md`; do not represent unsupported
   canary or artifact surfaces as live proof.

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
installed-smoke slice adds the three focused skill-hook cases and bounded live
draw evidence above. No exhaustive shard, Linux host, or hosted workflow ran.

## constraints

- The real Store migration already ran from exact merged main `f76050d7`; do
  not rerun or edit it manually. Preserve the named backup.
- Hosted CI is not authorized or needed for this local gate package. Claude
  authentication is restored; no further Windows draw belongs in this package.
- OpenClaw and Hermes remain explicitly deferred to the later Linux handoff.
- Do not mutate or clean the primary checkout or unrelated worktrees.
- Do not change provider routing, Option A pins, AR-119 matrix cells, or
  previously consumed live evidence.
- Do not carry recruiter-only closest-worker or selection-evaluation prose into
  native child context.
