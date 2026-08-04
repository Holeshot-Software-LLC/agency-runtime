---
title: "AR-236 active recovery capsule"
status: active
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [handoff, cli, dashboard, parity, operations, recovery]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/main.py
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/server/http.py
  - agency_runtime/core/dashboard_operational.py
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-236
branch: main
evidence_commit: 74a24d08ab5991080487de4c55773c54d3bc59ee
minimum_ledger_commit: 74a24d08ab5991080487de4c55773c54d3bc59ee
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245
---

# AR-236 active recovery capsule

Bounded current-state projection for the CLI/dashboard parity task.
The [canonical issue](../issue-AR-236-achieve-full-cli-dashboard-parity.md)
owns the full acceptance history; the
[parity analysis](../../analysis/2026-08-04-cli-dashboard-parity.md) owns
the gap inventory.

## checkpoint

- Planning pair exists in the working tree: the AR-236 issue, the
  parity analysis, the AR-236 capsule, the registry updates, and the
  AR-235 reciprocal `related` link. Branch `main` resolves to commit
  `74a24d0` (the AR-235 worklog reconciliation). No AR-236
  substantive code, test, or config change has landed yet.
- Tracker is live: [issue #245](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/245)
  carries the full AR-236 body and matches the local planning record.
- The analysis doc identified 10 sub-issues, prioritized by impact ×
  cost. The first three (hiring list/show, promotion readiness,
  duplicates/consolidate) are the highest-impact lowest-cost wins.
- Two untracked helper files remain in the working tree:
  `scripts/strip-frontmatter.ps1` and
  `scripts/strip-frontmatter-235.ps1` (one-shot PowerShell helpers
  used during AR-235 setup). They are unrelated to AR-236 and
  should be cleaned up at the operator's convenience.
- Slice 1 of AR-235 (per-stage inference profile schema + route
  resolution) appears to have been implemented in another session
  context: 486 lines of code changes across 6 files plus a new
  `agency_runtime/core/inference_profiles.py` are uncommitted in
  the working tree. These are NOT part of AR-236; they are an
  AR-235 deliverable awaiting their own commit set, validation,
  and PR.

## completed-evidence

- The full CLI surface is documented from
  `agency_runtime/cli/parser.py` (13 command groups) and
  `agency_runtime/cli/main.py` plus 9 handler modules. 50+ top-level
  commands with subcommand trees.
- The full dashboard surface is documented from
  `agency_runtime/dashboard/index.html` (6 view panels, 3 modals),
  `dashboard-render.js` (render functions per view), and
  `dashboard-actions.js` (9 API endpoints the dashboard actually
  calls).
- The 10-item gap list is captured in the analysis doc with
  per-item priority, cost, and recommended first slice.
- The user's three open questions are answered and recorded in the
  issue's "Current state" section: eval is dev-only, "pretty CLI"
  is `rich`-style cards, phrase-typed confirmation is the canonical
  destructive-op pattern.
- AR-235 and AR-236 are now reciprocally linked: AR-236's gap
  list includes a duplicate-detection sub-issue that consumes
  AR-235's `amend_overlap_threshold`; AR-235's planning record
  links to AR-236 as a peer concern.

## exact-blocker

- The planning pair is uncommitted. Per AGENTS.md "A commit cannot
  contain its own SHA," the worklog ledger commit records the
  substantive commit, not itself.
- No sub-issue work has started. The user authorized the planning
  pair; sub-issue work awaits greenlight per sub-issue.
- Sub-issue 9 (Upgrade) is substantial and may warrant its own AR
  with dedicated scoping; do not bundle it with a smaller
  sub-issue's PR.
- Sub-issue 10 (CLI presentation richness) requires a presentation
  library decision (likely `rich`); an ADR is needed before
  implementation begins.
- The uncommitted AR-235 slice 1 code in the working tree is not
  AR-236 scope. It needs its own commit set, validation, and PR
  against the AR-235 plan, not this one.
- Tracker creation/closure for any sibling "pending authorization"
  AR remains blocked on operator authorization.
- No automatic CI ran for this planning work. Exhaustive coverage,
  the four-shard 97% coverage gate, and the six-interpreter
  compatibility matrix are `workflow_dispatch`-only and were not
  requested.
- The 3 pre-existing `verify_docs.py` worklog errors
  (`e87747d` missing, `4928a87` encoding) are not introduced by
  AR-236 and are out of scope here.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this
task. Continue the same persistent goal from the planning pair
through normal compaction. Subsequent sub-issues await explicit
user greenlight per sub-issue.

## next-bounded-work-package

1. Commit the planning pair (AR-236 issue, parity analysis,
   AR-236 capsule, registry updates, AR-235 reciprocal `related`
   link) as one substantive commit.
2. Commit the worklog update + registry backref as the matching
   `docs(worklog):` ledger commit.
3. Push the pair to `origin/main`; verify the registry still
   resolves; `gh issue view 245` to confirm tracker parity.
4. Pause for user greenlight before opening sub-issue 1
   (Hiring list / show). The proposed sub-issue order is
   listed in the analysis doc §"Top-priority gaps."
5. After the planning pair is pushed, address the uncommitted
   AR-235 slice 1 code separately — its own commit set,
   validation, and PR.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
gh issue view 245 --repo Holeshot-Software-LLC/agency-runtime --json state,labels
git diff --check
# After commit + push:
python scripts/update_worklog.py --check
# After sub-issue 1 lands, add the relevant fast spine
# (test_workforce_dynamic_hiring, test_workforce_hiring_contract,
# test_workforce_selection_safety, test_workforce_promotion,
# test_routing_correctness) to the validation list.
~~~

## constraints

- No push, PR, hosted dispatch, publication, tracker mutation,
  tag, release, trust-store action, or repository setting
  change without authorization.
- Do not start sub-issue work without explicit user greenlight.
- Preserve the 12 KiB / 180-line hard cap. If the next
  sub-issue's state does not fit, archive this capsule under
  `docs/roadmap/handoffs/archive/` and start a fresh one with
  a new SHA pair, per AGENTS.md.
- Keep AR-236 in `open` until every acceptance item has current
  evidence. Do not mark it `done` on the strength of the
  planning pair alone.
- Do not delete or rewrite any planning artifacts (AR-236 file,
  analysis doc, registry rows, this capsule) without first
  moving them to `archive/`. The historical record is the
  source of truth.
- Do not introduce live-evaluation admission or modify
  `hard_checkpoint_percent`. The fixed 50% threshold is the
  only field accepted by the capsule schema.
- Sub-issue 10 requires an ADR for the presentation library
  decision before implementation begins.
- Sub-issue 9 (Upgrade) is substantial; do not bundle it with
  smaller sub-issues.
