---
title: "AR-207: Persist preflight and delegation failure diagnostics"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [product, evidence, preflight, delegation, codex, diagnostics]
related:
  - README.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/roadmap/issue-AR-206-accept-bounded-ready-routing-receipts.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-207
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
depends_on: [AR-206]
blocks: [AR-203, AR-204, AR-205]
---

# AR-207: Persist preflight and delegation failure diagnostics

## Problem

An Agency-enabled Codex turn can terminate as `preflight_failed` while the
authoritative Store retains only that terminal status. The exception class,
bounded stage/reason, and attempted inference receipt are discarded. Codex can
then complete an empty turn, and product evidence cannot distinguish provider
timeout, invalid inference, context construction, or ready-commit failure
without another live run.

The exact installed product trial for merge
`6b49f17d6787823f9ba78a8f09383001b6a77535` proved a separate downstream
failure. Inference accepted a nine-specialist team, but no activation grant,
specialist load, worker run, or native spawn/wait followed. Stop correctly
finalized `delegation_declined`, yet the deleted isolated Codex profile and
content-free result projection retained too little evidence to identify why
the parent emitted no delegation tool call or response.

## Current state

- Diagnostic trace `019fb83f-3aa8-78f2-8f7c-06aaf71a7f0c` lasted 91.146
  seconds and ended `preflight_failed`. It has one `runs` row, no route, and no
  model receipt. `fail_preflight_attempt` clears the attempt fields and does
  not persist the caught failure.
- Product trace `019fb832-5f01-75d0-a3fe-e51bb2816771` retained accepted route
  `ad20ea5c-c547-485a-89a6-f8e1372252e7`, eight work units, nine specialists,
  and eight suggested delegations. It retained zero grants, consumptions,
  loads, worker runs, or native spawn/wait events, then finalized
  `delegation_declined` with missing `delegation_execution`.
- A control with Agency disabled returned exact `PROBE_OK` on `gpt-5.6-sol`,
  excluding parent Codex authentication, model availability, and basic host
  execution as the shared cause.
- The successful exact-build activation trace separately proves hook routing,
  one native specialist lifecycle, accepted finalization, and zero corrections.
  The defect is therefore request/path-specific, not a blanket installation
  failure.
- The local repair now persists schema-v39 `agency.preflight.failure.v1`
  receipts and projects them through exact activation, CLI, and dashboard
  evidence. Raw prompts, responses, errors, paths, and credentials are excluded.
- The product harness now grades one through sixteen exact inferred work units
  instead of applying the fixed one-child activation canary. Every planned row
  must reach its own persisted child, activation, load, worker, and completed
  delegation; a parent-side non-collaboration tool call fails the trial.
- Product execution now has a 600-second minimum and retains the 1,800-second
  CLI default. README, troubleshooting, and ADR-0124 describe the same
  no-generalist contract.
- PR 197 merged exact revision
  `3b5a00f7564e29aaf0ec68bd09547f8b8fa42c2e`, and that VCS revision was
  exact-installed for Codex, ZCode, and dashboard. Its activation execution
  selected `code-reviewer`, completed one grant, load, worker, native child,
  delegation, and accepted finalization with zero corrections, but proof
  misclassified one Codex stdout `error` item as a non-allowlisted tool.
- The authoritative parent rollout contains only `spawn_agent` and
  `wait_agent`. Codex 0.146 serializes non-critical warnings as completed
  `error` items; the exact canary catalog shortened 11,805 description
  characters across 67 skills, averaging 177 characters per skill and
  deterministically crossing Codex's 100-character warning threshold.
- The bounded repair classifies the exact hook-bypass and
  skill-catalog-shortening messages as content-free host notice types. Unknown
  `error` items and non-collaboration tools remain unexpected and fatal.
- Two bounded review passes found no remaining behavior defect. All 25
  warning-strict activation-canary tests pass, and all 63 curated decision
  mutations are killed with zero survivors or invalid mutations.
- The exact checkpoint passed the named fast spine: 636 warning-strict Python
  tests passed with six skips, dashboard UI passed 110 tests, documentation
  validated 584 files, Ruff checked and formatted 603 files, routing passed
  every gate, decision conformance passed with source unchanged, and diff
  integrity passed.

## Approach

1. Persist exactly one bounded, content-free preflight failure receipt before
   cleanup. It records an allowlisted stage and reason, safe exception category,
   and provider/model attempt status without prompt or response content.
2. Project that receipt through exact activation, product evidence, CLI status,
   and dashboard diagnostics so `preflight_failed` never collapses to only
   `route_not_found` or an unexplained empty turn.
3. Preserve bounded Codex hook and turn-event facts needed to distinguish
   context injection, model output, native spawn/wait, and Stop reconciliation.
4. Use those diagnostics plus bounded controls to repair the first demonstrated
   product execution boundary. Keep the fixed activation canary separate from
   bounded multi-unit product grading, dispatch every accepted row exactly once,
   and fail if the parent performs product work.
5. Distinguish exact known Codex non-critical host notices from tool items,
   preserve only allowlisted notice categories and counts, and reject every
   unknown `error` item.
6. Keep inference authoritative, the parent non-generalist, and all raw prompt,
   provider-response, stderr, path, and credential material out of durable
   evidence.

## Dependencies

AR-206 is complete in the exact installed build and proves wide ready receipts
can be read without correction. AR-203 owns workspace-write/product proof,
AR-204 owns the integrated README story, and AR-205 owns inference-first exact
staffing. This issue owns only failure observability and the execution boundary
those proofs exposed.

## Acceptance

- [x] Every `preflight_failed` run has one correlated, bounded, content-free
  failure receipt.
- [x] Failure evidence retains no prompt, provider response, exception message,
  filesystem path, credential, or raw stderr.
- [x] Exact product evidence reports the failed stage and allowlisted reason
  instead of only `route_not_found` or an empty turn.
- [x] Accepted-route/no-delegation evidence distinguishes missing parent spawn
  from hook injection, child activation, and Stop failure.
- [x] Focused warning-strict tests and the named fast spine pass.
- [x] Curated mutations prove removal, overbroad retention, and projection
  regressions fail.
- [x] Exact known Codex non-critical notices are content-free and traceable;
  near-miss or arbitrary `error` items remain fatal.
- [x] The host-notice repair passes the named fast verification spine.
- [ ] The Codex host-notice repair is reviewed, merged, and exact-installed
  before any fresh product trial.
- [ ] One fresh exact-build product trial reaches native delegation and writes
  its workspace artifacts with zero response corrections.
