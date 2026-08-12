---
title: "AR-218: Fund one bounded repair per workforce inference stage"
status: done
category: roadmap
created: 2026-08-01
updated: 2026-08-12
tags: [bug, product, inference, workforce, configuration, budgets]
related:
  - README.md
  - agency_runtime/core/config.py
  - agency_runtime/core/config_defaults.yaml
  - agency_runtime/core/configuration_schema.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/installer_payloads.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_workforce_inference.py
  - tests/test_configuration.py
  - tests/test_native_installer.py
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-218
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/219
depends_on: [AR-217]
blocks: [AR-203, AR-204, AR-219, AR-220]
---

# AR-218: Fund one bounded repair per workforce inference stage

## Problem

Exact merged and installed build
`8cfd9751aa7290362b6e3fcdec60adc81315617c` passes autonomous Codex
activation. Its single governed README product trial still terminates during
workforce inference because fast mode shares three calls across planner and
recruiter.

The live sequence rejected the first planner response, accepted its bounded
repair, then rejected the first recruiter response. The recruiter already owns
one bounded repair, but no fourth call remained to execute it. Separate tests
proved each stage's repair with the other stage succeeding first try; no test
composed both allowed repairs in one route.

## Current state

Trial `ar217-8cfd975-readme-01` is consumed and terminal `NO-GO` after 101.1
seconds. Session `019fbc05-3cf8-7b83-b6ca-1e280067f0a6`, trace
`019fbc05-3d81-74a3-a532-ba613b2a7846`, and run
`682ee08f-9663-466a-8d86-16fd01ea3492` retain planner rejection, planner
repair, and recruiter rejection through
`codex-subscription/gpt-5.6-luna`. The terminal reason is
`workforce_inference_failed`; staffing is `inference_invalid`.

Atomic failure preserved zero route, specialist, delegation, finalization,
header, or workspace-write evidence. Correction count zero is not success
because parent generation never began. This exact build and trial must not be
rerun.

Implementation commit `583ebc8` and ledger `095e244` are a clean local
checkpoint. The named fast gate passes 643 Python tests with six skips, all 110
dashboard UI tests, all routing gates, 612-document validation, and repository-
wide Ruff lint/format. Decision conformance passes its baseline, kills all 73
curated mutations with zero survivors or invalid cases, and reports
`source_unchanged=true`.

Exact-head Codex review found one compatibility defect at
`discussion_r3694929406`: a previously valid partial balanced-only cap of three
would be compared against the new implicit fast default of four and rejected.
The repair validates the omitted fast value against the explicit balanced cap
and applies the same cap during default merging without rewriting the persisted
document. Its exact regression and adjacent default/update checks pass eight
tests.

Repaired checkpoint `a347eff` passes the complete named gate: 643 Python tests
with six skips, 110 dashboard tests, 39/39 routing gates, and 73/73 killed
decision mutations with zero survivors or invalid cases. The target default-
budget mutation is killed and the evaluator reports `source_unchanged=true`.
All documentation, Ruff lint/format, and diff checks pass.

PR 220 passed exact-head Codex review and merged normally as
`f8e607d309f5dba933bc55f17892209e39e6e014`. That immutable revision is
installed as `0.1.0+gf8e607d309f5`, and this machine's explicit fast budget is
four. Bare installation selected only Codex, ZCode, and dashboard. The
dashboard service is current, active, and reachable.

The exact build's one autonomous activation passed on its first attempt with an
inferred `code-reviewer`, one completed native delegation, a valid first
header, zero corrections, `autonomous_bypass`, and no persistent trust change.
Its one product trial, `ar218-f8e607d-readme-01`, then accepted an eight-unit
plan and recorded eight completed child workers. The product projector rejected
that topology, the first header was absent, and the isolated workspace remained
empty. AR-219 owns that later independent boundary; this build and trial are
consumed and must not be rerun.

## Approach

1. Raise only the fresh fast-mode total from three calls to four so planner and
   recruiter can each use their existing one-repair ceiling.
2. Keep balanced at four and strict at five; strict's fifth call remains the
   independent staffing critic.
3. Preserve every explicit persisted budget, including lower cost or latency
   opt-outs. A legacy balanced-only partial cap bounds an omitted fast default;
   do not migrate operator-owned configuration silently.
4. Prove the exact composed sequence and bind generated hook timeouts to the
   effective four-call budget.
5. Mutate the typed default back to three in decision conformance and require
   the composed regression to kill that drift.

## Dependencies

AR-217 owns the independent hiring-critic evidence handoff. ADR-0118 keeps
online staffing inference-owned. ADR-0132 supersedes ADR-0114's one-shared-
repair fast default without weakening either stage's bounded correction rule.

## Acceptance

- [x] Fresh bundled, dataclass, loader, and partial-validation defaults use a
  four-call fast workforce budget.
- [x] Explicit lower budgets remain operator-owned and unchanged.
- [x] A legacy partial `balanced_call_budget: 3` document remains valid, loads
  an effective fast budget of three, and is not rewritten.
- [x] A composed default-fast regression accepts planner rejection/repair plus
  recruiter rejection/repair and records exactly four attempts.
- [x] No deterministic staffing fallback or unbounded retry is introduced.
- [x] Generated host timeouts derive from the effective four-call budget.
- [x] Focused verification, two bounded review passes, and the named local fast
  gate pass on one exact head.
- [x] One exact merged build passes autonomous activation and at most one fresh
  README product trial with specialist delegation, workspace write, a valid
  first header, zero corrections, and independent artifact checks.
