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
evidence_commit: eb8e07770bf2b1d29933ff7730f09115928e4b1a
minimum_ledger_commit: 73274832a0985c7817c991061ac839386deb7cc1
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
- Exact `8097e77` consumes one autonomous-bypass activation and passes. Session
  `019fc036-6716`, trace `019fc036-733e`, native run
  `codex-agent:019fc037-8811`, and delegation `f4f618db` prove an inferred
  `code-reviewer`, one exact spawn, one execution follow-up, two waits, a
  completed exit-zero worker, valid first header, zero corrections, and zero
  unexpected parent items. Trust bypass changes no persistent profile state.
- Product trial `ar223-8097e77-readme-01` is consumed and fails after 104.094
  seconds. Session `019fc03e-1ce0`, trace `019fc03e-1d71`, run `c100183d`,
  route `52f57ced`, and finalization `bd418651` prove an accepted 11-unit plan
  across seven specialists. The parent rollout is observed, but it makes zero
  spawns, follow-ups, or waits; no specialist loads or workers exist; the
  workspace is empty; the header is absent; and correction count is zero.

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
- PR 233 merges exact `8097e7708a52956862746ea3aa5b2fecbe7031ed` and the
  global uv receipt names that exact revision. Default-suite installation
  refreshes Codex bundle `a9aa4f7e...`, registers/enables ZCode, and leaves the
  dashboard active and reachable. Codex global guidance is byte-equal to the
  canonical 1,123-byte renderer with one begin and one end marker. Codex is
  installed; the build then passes its single autonomous activation with one route,
  plan, delegation, load, worker, and finalization; no preflight failures; a
  valid first header; and zero corrections. Its consumed product trial proves
  an accepted 11-unit inferred graph and exact isolated trust, then fails
  `codex_parent_spawn_missing` / `workspace_write_not_proven` before execution.
- The first missing edge is Codex's default 2,500-token hook-context spill, not
  selection or guidance loading. The one-row activation fits; the 11-row plan
  spills beyond the collaboration-only parent. The repair sets
  `additionalContextLimit: 0` only for Codex `UserPromptSubmit` while Agency's
  32,000-character bound remains; focused checks pass 200 tests and Ruff.
- Clean recovery head `7327483` passes the complete named local gate for that
  repair: 629-document validation, Ruff over 609 files, Python 657 passed with
  6 skipped, dashboard 110/110, every routing threshold, and conformance with
  every mutation killed, none invalid, and source unchanged.

## exact-blocker

The README main story remains NO-GO. PR 234 merges and uv installs exact
`eb8e077`; bare install discovers only Codex and ZCode, enables both, and leaves
the dashboard active and reachable. Its installed Codex manifest has the exact
inline-plan field only on `UserPromptSubmit`. Codex remains
`activation-required`; exactly one autonomous activation and one fresh product
trial remain. Either failure is the stop point, not another repair loop.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Run one autonomous activation and checkpoint its exact result.
2. Run one fresh product trial; stop and report on either failure.

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
