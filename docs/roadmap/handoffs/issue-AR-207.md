---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-08-01
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-211-bound-immutable-commit-resolution.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-216-preserve-required-product-scenario-files.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0133-treat-product-specialist-loads-as-turn-scoped.md
  - docs/decisions/0134-bind-contractor-risk-to-validated-authority.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: b2be07758737b8e89a98aa0b0e03cecd6eb68c83
minimum_ledger_commit: 38c757eedb38713753028127ddc7edfdc96e0b9e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` AR-223's parent
  `Stop` repair reconciles exact second-turn execution without a synthetic
  second `SubagentStop`; exact `62ea12a` passes the named local gate and two
  bounded reviews.
- PR 232 merges that tree as `b2be077`. Independent install provenance matches
  the merge; bare install refreshes Codex, enables ZCode, and runs an active
  reachable dashboard.
- The consumed `b2be077` activation passes. Session `019fbfd8-bb78`, trace
  `019fbfd8-c7ec`, run `ee965317`, delegation `8b17ef05`, and child
  `019fbfd9-8678` prove inferred/loaded `code-reviewer`, exact execution, a
  closed exit-zero worker, valid first header, zero corrections, and autonomous
  trust without persistent change.
- Product trial `ar223-b2be077-readme-01` is consumed and fails. Session
  `019fbfdf-0069`, trace `019fbfdf-00fa`, run `c77ede95`, route `37d9b5bc`, and
  finalization `3b0bed95` prove an accepted eight-specialist inferred plan, but
  zero spawns, follow-ups, waits, loads, or workers. The workspace is empty;
  failure is `codex_parent_spawn_missing` / `workspace_write_not_proven` with
  no header and zero corrections.

## completed-evidence

- Exact `62ea12a`: Python 656 passed/6 skipped, dashboard 110/110, 628-document
  validation, repo-wide Ruff lint and format, all routing thresholds, and
  decision conformance 90/90 killed with zero invalid results.
- Earlier exact `43870c8` proves an accepted contractor hire and eight-unit
  topology but not execution. Exact `b2be077` closes activation execution; its
  product trial now isolates the remaining parent-authority regression.
- The managed global-guidance slice is focused-green: 248 broader installer,
  uninstall, canary, product-host, adapter, and decision tests pass; the final
  21-test targeted rerun passes; Ruff passes; documentation validation covers
  629 files; and the new decision mutation is killed 1/1. Two review passes are
  closed. No persistent Codex profile or live trial has consumed this build.
- Clean recovery head `9f391b8` passes the complete named local gate: 629
  Markdown documents, repo-wide Ruff over 609 files, Python 657 passed with 6
  skipped, dashboard 110/110, every routing threshold, and decision conformance
  91/91 killed with zero survived or invalid results and source unchanged.

## exact-blocker

The README main story remains NO-GO. Exact `b2be077` passes activation, but its
product parent never invokes collaboration. ADR-0126's developer instruction
does not satisfy current Codex's user-or-applicable-instruction delegation gate.
A broad-skill probe adds a forbidden parent shell read and remains untraceable.
The managed global-guidance path now installs, plans, projects, uninstalls, and
rolls back under focused tests and the complete named gate. It is not yet merged,
installed into the current Codex profile, or proven by fresh live evidence.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Publish the already authorized PR, merge exact green head, and install that
   exact merge into the current Codex, ZCode, and dashboard scope.
2. Spend one fresh activation and at most one product trial. Never rerun the
   consumed `b2be077` evidence.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
.venv\Scripts\agency.exe eval routing --json --no-details
.venv\Scripts\agency.exe eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Product host remains sandboxed to the exact trial workspace.
- Only Codex, ZCode, and dashboard are in machine scope.
- One live product trial per exact installed build; any correction is failure.
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, `9c2e9f8`, `8cfd975`,
  `f8e607d`, `386afca`, `5c45f154`, `ff39761`, and `43870c8` consumed governed
  live evidence; exact `ba76ce7`, `a2d1a7c`, and `5ff4a08` also consumed their
  activations; exact `b2be077` consumed both activation and product evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
