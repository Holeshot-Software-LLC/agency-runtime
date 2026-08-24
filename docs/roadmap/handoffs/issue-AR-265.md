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
evidence_commit: ca517872a3b55fa21a4350c841f35c6cba44ac9d
minimum_ledger_commit: e48777e8e2a1668c84cce343eee24fdde1a61bd8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317
---

# AR-265 active recovery capsule

## checkpoint

- Isolated worktree branch `codex/ar265-contextual-turn-classification` starts
  at exact fetched `origin/main` `4a3267738bb20519500513ea1498fc68f8ea9443`.
- The shared main checkout remains untouched with another worker's OpenClaw
  changes preserved in place.
- Telemetry reported 20.8 percent remaining after bootstrap, so this package
  required a clean substantive and ledger checkpoint. That pair now exists at
  `faba05bbb97f91a87730e3b1e223cf156432d9c2` and
  `a19098a9978ec2e43c0e24256b69caeab717fa50`.
- End-of-package telemetry reported 61.1 percent remaining and
  `continue_same_task`; no new hard checkpoint was required.
- Post-review telemetry reported 38.8 percent remaining, requiring another
  clean checkpoint. The review repair and its ledger now exist at
  `ca517872a3b55fa21a4350c841f35c6cba44ac9d` and `e48777e8`.

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
- Two bounded independent review passes found finite-phrase advisory gaps,
  direct-action false advisories, permissive context fields and versions, and
  an overly narrow lifecycle enum. The repair uses a closed structural grammar,
  targeted action guards, exact-key schemas, exact integer versions, and a
  bounded legacy-compatible status identifier; every finding has a regression.
- The final focused classifier, selector, Store, and workforce-inference slice
  is green: `268 passed`.
- The final named fast production spine is green: `806 passed, 20 skipped` in
  `145.76s`. The unchanged dashboard UI gate remains `134/134`, and the final
  worktree-local routing evaluation passes every accuracy, latency, scale, and
  startup gate.
- The final worktree-local decision-conformance evaluator passes its baseline
  in `227.796s` and kills all `151` curated mutations with `0` survivors, `0`
  invalid cases, and unchanged source. One earlier post-review invocation used
  the shared editable console executable, stopped at a stale baseline test node
  with zero mutations executed, and is not counted as evidence.
- Documentation metadata (`734` files), policy availability, Ruff check, Ruff
  format (`683` files), and diff hygiene pass. Worklog and aggregate docs parity
  also pass after recording the substantive commit; metadata validation now
  covers `735` Markdown files.

## exact-blocker

Tracker [#317](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317)
now exists. The owner authorized the previously listed branch push, pull
request, merge, exact-main installation, and bounded live contextual-routing
canary on 2026-08-24. None is complete yet, and this capsule still does not
claim installed-host or reviewed-pull-request evidence.

## same-task-continuity

Keep contextual inquiry classification separate from execution topology.
Inference chooses specialists; deterministic policy only constrains advisory
work to a read-only parent assessment. The header reports the completed current
turn route; it does not trigger routing. Do not touch the shared checkout or
reinterpret unrelated OpenClaw evidence as AR-265 verification.

## next-bounded-work-package

1. Commit tracker #317 linkage and its exact worklog ledger, then push the clean
   branch and open the governed pull request.
2. Observe required checks and review state before merge. After a verified
   merge, refresh exact main, install it, and run the bounded live header plus
   correlated Store canary without reusing local source evidence as host proof.

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

- Outward authorization is limited to tracker #317 linkage, this branch push,
  its pull request and merge, exact-main installation, and the bounded live
  contextual-routing canary. Do not dispatch unrelated hosted workflows.
- Do not mutate, clean, switch, or commit the shared main checkout or any other
  worker's files.
- Do not weaken advisory planning to permit workspace or external writes.
- Do not claim a live installed-host proof from local source tests.
