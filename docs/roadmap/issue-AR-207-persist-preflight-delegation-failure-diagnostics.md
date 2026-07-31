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
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0125-admit-only-exact-content-free-codex-host-notices.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-207
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
depends_on: [AR-206, AR-208]
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
- PR 198 merged that repair as exact revision
  `5328070cd048f42ce88e3bcb16e42f1e69cfae24`, which was then installed as an
  official VCS package. The default full-suite install discovered only Codex
  and ZCode, registered both, installed and reached the dashboard, and left
  only the attended Codex activation ceremony incomplete as designed.
- Autonomous activation session `019fb90b-dc97-7db0-891a-3aeea357ed3b`, trace
  `019fb90b-e95d-7bf2-84ae-fd0efb150816`, again completed the exact
  `code-reviewer` grant, load, native child, delegation, accepted finalization,
  and zero-correction header. Attestation still failed because Codex emitted
  the packaged `2% skills context budget` spelling rather than the generic
  packaged spelling admitted by the first repair.
- A bounded raw-JSONL diagnostic reproduced exactly two hook-bypass notices and
  one `2%` skill-catalog notice with Codex exit zero. The installed binary
  contains both the generic and `2%` sentences. The follow-up therefore adds
  only the exact `2%` sentence to the same fixed notice type; arbitrary and
  one-character near-miss errors remain fatal. All 25 activation-canary tests
  pass after the follow-up.
- The follow-up named fast gate is green: 636 warning-strict Python tests
  passed with six skips, dashboard UI passed 110 tests, documentation validated
  584 files, Ruff checked and formatted 603 files, routing passed every gate,
  and all 63 curated mutations were killed with zero survivors or invalid
  mutations. Decision conformance restored the source unchanged.
- PR 199 merged the exact-sentence follow-up as revision
  `5ad4aef8444d1437e2a29c1e9ac4df46dce7229f`. The official VCS package was
  exact-installed, and the default full-suite refresh again discovered only
  Codex and ZCode while keeping the dashboard reachable.
- Autonomous activation session `019fb92a-8143-7772-97a6-03cc880685c0`, trace
  `019fb92a-8d72-7f33-a30a-19d8480dbd64`, passed on that exact build. It
  selected `code-reviewer` through inference and persisted one grant,
  consumption, load, native child, completed delegation, accepted finalization,
  valid first-pass header, zero corrections, and proven Store evidence. The two
  admitted notice types accounted for all three host notices; no unexpected
  item remained.
- The one allowed product trial on `5ad4aef`, trial
  `ar207-5ad4aef-readme-01`, is a terminal `NO-GO`. Session
  `019fb92d-694c-7e42-b553-ee53802bac99`, trace
  `019fb92d-69c3-7541-bc96-ae0c72126a25`, and run
  `56389325-9128-470b-945c-b3951bc37248` ended `preflight_failed` at stage
  `routing` with reason `routing_failed`, exception category
  `validation_error`, and zero provider attempts. No route, tool, response,
  header, or workspace write was produced. Correction count remained zero.
- The zero-attempt receipt did not prove that inference was never invoked.
  A no-call replay of the exact 2,322-character wrapped prompt reached the
  structured-provider boundary, disproving the earlier pre-provider diagnosis.
- A fresh online replay against a private SQLite backup then completed planner
  and recruiter calls on `gpt-5.6-luna` in 73.607 seconds. Session
  `a851fa51-aff6-4f9a-8f6f-7941d0af7111`, trace
  `53c878e2-37e3-4c4d-ac0e-708c1e7fe72c`, and run
  `24a13190-37dc-40b0-85b8-e87ec3ad75ae` reached `ready` with eight inferred
  work units and eight fitting specialists: `codebase-onboarding-engineer`,
  `python-application-engineer`, `typescript-application-engineer`,
  `software-test-engineer`, `code-reviewer`,
  `application-security-engineer`, `application-integration-verifier`, and
  `technical-writer`. The replay was preflight-only; it did not claim native
  launch, delegation, product artifacts, or a product-trial pass.
- The exact installed routing sources match the checkout byte-for-byte. The
  consumed failure is therefore response- or state-specific and is not
  currently reproducible as a deterministic routing defect. It remains a
  terminal `NO-GO`; no product trial may be rerun on `5ad4aef`.
- All four previously unresolved PR 198 Codex threads now have evidence-backed
  replies and are resolved. The valid product-evidence gap is fixed by
  `947dafb`; AR-208 maps to tracker #200 and ADR-0125. The alleged worklog
  ancestry defect was closed only after Git proved both recorded commits are
  ancestors of the reviewed revision.
- The repaired branch is locally fast-green. The focused product-host suite
  passed 20 tests; the named warning-strict Python spine passed 636 tests with
  six skips; dashboard UI passed 110 tests; documentation validated 587 files;
  Ruff checked and formatted 603 files; and `git diff --check` passed. The
  workspace CLI routing evaluation passed every gate, including 1.116 ms
  cache-hit p95, while decision conformance passed its baseline, killed all 64
  curated mutations, retained zero survivors or invalid cases, and proved the
  source tree unchanged.
- PR 201 merged the repair with commit-preserving ancestry as exact revision
  `dd85e7d981f9214104c61815b49f51e178896295`. The official VCS package is
  exact-installed. Bare install discovered and registered only Codex and ZCode,
  then recreated, started, and reached the per-user dashboard; its only
  incomplete component was the designed Codex activation continuation.
- Supported-bypass activation session `019fb978-1242-7c30-9c93-38751f4f26ff`,
  trace `019fb978-1ec4-7f91-a9b2-9ab47abb15d8`, and run
  `810eab84-69f2-4bdd-a711-1eb8a59bcc89` passed on that exact build. Inference
  selected `code-reviewer` and persisted the route, grant, consumption, load,
  native child, worker, completed delegation, and accepted finalization. The
  first-pass header was valid, Store evidence was proven, correction count was
  zero, and all three Codex host notices mapped to the two admitted types.
- The one allowed product trial on `dd85e7d`, trial
  `ar207-dd85e7d-readme-01`, is terminal `NO-GO`. Session
  `019fb982-a686-79d1-bc6c-f605e64895fc`, trace
  `019fb982-a702-7c11-b527-a4b5fa603250`, and run
  `ec15beed-4ed4-4bc8-bdf6-1a19e4b4d926` reached ready with eight inferred
  units and eight selected specialists. All eight delegation rows remained
  `suggested`; no grant, consumption, specialist load, worker run, native child,
  or completed delegation followed. Codex exited zero with no response or
  header, workspace trust and hook bypass were proven, workspace write was not,
  and correction count was zero. The first failed boundary is therefore the
  accepted-plan to parent-native `spawn_agent` handoff, not selection.

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
- [x] Both exact Codex-packaged skill-catalog notice spellings pass the named
  fast spine and the arbitrary-error mutation remains killed.
- [x] One fresh exact-build activation canary accepts the current Codex host
  notices without admitting an unknown error.
- [x] The complete Codex host-notice repair is reviewed, merged, and
  exact-installed before any fresh product trial.
- [ ] One fresh exact-build product trial reaches native delegation and writes
  its workspace artifacts with zero response corrections.
