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
branch: codex/ar265-live-evidence
evidence_commit: 90b852bdaa2ee1b9d02f61dff9f561a5c165bac4
minimum_ledger_commit: 9dcea6159218785bd347a376f3f5efece18fb5ea
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317
---

# AR-265 active recovery capsule

## checkpoint

- Pull request [#318](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/318)
  passed all automatic checks and merged without admin override on 2026-08-24.
  Fetched `origin/main` is exact merge
  `90b852bdaa2ee1b9d02f61dff9f561a5c165bac4`, whose reviewed second parent is
  exact branch head `9dcea6159218785bd347a376f3f5efece18fb5ea`.
- This evidence checkpoint runs in a second isolated worktree on
  `codex/ar265-live-evidence` from that exact merge.
- The shared main checkout remains untouched with another worker's OpenClaw
  changes and untracked evidence files preserved in place.
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
- Documentation metadata (`736` files), policy availability, Ruff check, Ruff
  format (`683` files), and diff hygiene pass. Worklog and aggregate docs parity
  also pass after recording the substantive and tracker-linkage commits.
- Exact-main Codex-only installation completed with transaction success and
  adapter `0.1.0+codex.0b797ab9d097`; dashboard and every non-Codex host were
  excluded. Deterministic Codex smoke passed `4/4` and verified all eight hook
  contracts. The install correctly reported restart-required activation.
- A genuinely fresh Codex CLI process, session
  `01a03637-d309-7ae1-9089-fc3b9e33cf0c`, ran the bounded two-turn canary. Its
  second trace `01a03639-4e34-7600-b710-3066ad9b7df9` classified exact prompt
  `what's next?` as classifier v5 `conversation` with selection and rerouting
  true, execution decision false, and a guard bound to the first trace.
- That second trace persisted exactly one `analysis/advise/read_only` unit,
  loaded exactly `code-reviewer` and `software-architect`, recorded successful
  `codex-fast/gpt-5.6-terra` receipts, zero delegation events, zero skill-load
  rows, and one `accept/completed` finalization.
- Desktop task `01a03632-60e0-7c53-8651-430d17561afe` exposed a stale running
  host process. Its first trace failed preflight and its second trace classified
  as `new_intent`; this is negative lifecycle evidence and is not counted as
  exact-main AR-265 proof.

## exact-blocker

Source, publication, exact-main Codex installation, and fresh Codex CLI runtime
evidence are complete. The remaining gate is a genuine Desktop-host proof after
a full application restart. This task cannot restart its own host without
terminating the active task, and the already-running process was demonstrably
stale. Tracker [#317](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/317)
therefore remains open; no Desktop pass is claimed.

## same-task-continuity

Keep contextual inquiry classification separate from execution topology.
Inference chooses specialists; deterministic policy only constrains advisory
work to a read-only parent assessment. The header reports the completed current
turn route; it does not trigger routing. Do not touch the shared checkout or
reinterpret unrelated OpenClaw evidence as AR-265 verification.

## next-bounded-work-package

1. Fully restart Codex Desktop, create a completely new task, and run the same
   bounded first assessment followed by exact `what's next?`.
2. Correlate its current-turn header with Store classification, source guard,
   specialist loads, model receipt, zero delegation, and accepted finalization.
3. If that exact-main Desktop proof passes, update this issue, close tracker
   #317 through an authorized documentation pull request, and preserve any
   remaining Desktop lifecycle defect under AR-263 rather than masking it here.

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
