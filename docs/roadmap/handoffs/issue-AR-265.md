---
title: "AR-265 active recovery capsule"
status: active
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [handoff, routing, classification, workforce, safety]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-265
branch: codex/ar265-contextual-turn-classification
evidence_commit: 4a3267738bb20519500513ea1498fc68f8ea9443
minimum_ledger_commit: 4a3267738bb20519500513ea1498fc68f8ea9443
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-265 active recovery capsule

## checkpoint

- Isolated worktree branch `codex/ar265-contextual-turn-classification` starts
  at exact fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`.
- The shared main checkout remains untouched with another worker's OpenClaw
  changes preserved in place.
- Telemetry reported 20.8 percent remaining after bootstrap, so this package
  must reach a clean substantive and ledger checkpoint before further work.

## completed-evidence

- The clean baseline focused slice had 104 passes and two existing failures:
  header authorization detection and the no-provider pending-authorization
  fail-open projection. Both are now repaired within this classification and
  receipt boundary.
- The candidate adds classifier v5 advisory selection, bounded read-only
  workforce planning, projection rejection for write authority, explicit host
  guidance, bounded unfinished-state carry-forward, and transcript-free typed
  subject context for planner and recruiter inference.
- Recipe/context policy v15 binds the context digest and exact prior source into
  the durable receipt and a ready-transaction guard. Historical messages and
  prose-bearing plan fields are excluded; content capture does not widen use.
- Advisory gap hiring is retained as internal staffing while native-child,
  workspace-write, and external-write authority remain forbidden.
- The expanded focused classifier, selector, Store, and workforce-inference
  slice is green: `226 passed`.
- The corrected named fast production spine is green: `806 passed, 20 skipped`
  in `135.02s`. The dashboard UI gate passes `134/134`, and the routing
  evaluation passes every accuracy, latency, and scale gate.
- The decision-conformance evaluator passes its baseline and kills all `151`
  curated mutations with `0` survivors, `0` invalid cases, and unchanged
  source. Its first restricted attempt could not attest disposable Windows
  scratch; the normal-host retry passed the complete evaluator.
- Documentation metadata (`734` files), policy availability, Ruff check, Ruff
  format (`683` files), and diff hygiene pass. Worklog and aggregate docs parity
  remain pending only because the substantive commit has not yet been recorded.

## exact-blocker

The code and canonical issue are not yet at a local recovery pair. GitHub issue,
push, pull request, merge, and hosted workflow actions remain unauthorized.

## same-task-continuity

Keep contextual inquiry classification separate from execution topology.
Inference chooses specialists; deterministic policy only constrains advisory
work to a read-only parent assessment. The header reports the completed current
turn route; it does not trigger routing. Do not touch the shared checkout or
reinterpret unrelated OpenClaw evidence as AR-265 verification.

## next-bounded-work-package

1. Create the local substantive commit and exact worklog ledger commit.
2. Refresh this capsule to those commits, independently review the resulting
   diff, and stop before any outward-facing action.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Do not create a tracker issue, push, open a pull request, merge, or dispatch a
  hosted workflow without explicit authorization.
- Do not mutate, clean, switch, or commit the shared main checkout or any other
  worker's files.
- Do not weaken advisory planning to permit workspace or external writes.
- Do not claim a live installed-host proof from local source tests.
