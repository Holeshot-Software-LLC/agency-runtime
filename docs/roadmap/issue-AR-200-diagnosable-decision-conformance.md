---
title: "AR-200: Make workforce decisions diagnosable and mutation-conformant"
status: in_progress
category: roadmap
created: 2026-07-29
updated: 2026-07-29
tags: [workforce, hiring, diagnostics, mutation-testing, inference, routing]
related:
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-200.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-200
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/175
depends_on: [AR-119, AR-199]
blocks: []
---

# AR-200: Make workforce decisions diagnosable and mutation-conformant

## Problem

The final AR-199 ordinary Codex trace proved relevant inference nominations for
seven of nine work units, but architecture hiring still collapsed every
post-parse candidate failure into `contract_invalid:candidate`. That code does
not identify whether employment revalidation, workforce projection, or causing
unit coverage rejected the candidate, and persisting raw provider content or
exception text would violate the evidence boundary.

The tests also pass while their ability to reject the exact historical
regressions remains implicit. Coverage and green examples do not prove that the
suite would catch configured-provider selection skipping inference, online role
anchor promotion, or contractor schema-boundary regressions.

The first AR-200 ordinary canary then proved a second opaque boundary:
architecture staffed correctly, but the sole documentation gap selected an
amendment and collapsed its post-parse rejection into
`contract_invalid:amendment`. The contract asked inference to choose an existing
target while separately allowing a model-authored contract identity, and its
strictly additive merge could exceed the smaller workforce list bounds.

## Current state

Configured workforce routing calls planner and recruiter, treats inference as
the online selection authority, and reserves deterministic typed staffing for
the visibly stamped no-provider floor. Contractor binding caps provider lists
at the employment schema and caps several projections at the smaller workforce
schema. The latest exact-installed live trace nevertheless rejected the sole
architecture hire with the generic candidate code, then exhausted the task's
one-hire budget before documentation hiring.

The repository has focused tests for the intended decisions but no mutation
conformance command. The upstream `rollinsio/beyond-test-coverage` project
demonstrates the useful principle of deliberately sabotaging a load-bearing
decision and requiring the relevant test to turn red. Its in-place
`git checkout` restoration model is not safe for an owner checkout and will not
be copied into Agency.

The implementation now reports content-free post-parse validation stages,
bounds only the smaller workforce routing projection by its UTF-8 byte limits,
and preserves the full validated employment contract for prompt compilation.
The new decision-conformance command rejects links and Windows reparse points,
requires a green baseline, creates a fresh private copy per mutation, and
admits a kill only for one ordinary failure of the expected test node.

Two focused review passes closed one isolation finding: the first version
preserved package links while copying. The final evaluator fails closed before
copying any linked package input. On the current branch, 108 focused workforce,
inference, selection, CLI, and conformance tests pass; the named Python spine
passes with 668 tests and 6 skips; the dashboard passes 109 tests; every routing
gate passes; and the final mutation proof kills 5 of 5 mutations with zero
survivors or invalid results and unchanged monitored source inputs. Normal
documentation validation passes for 536 files. Strict tracker validation still
reports the repository's pre-existing AR-128 through AR-198 parity backlog;
AR-200 itself is mapped to tracker issue 175.

PR 176 merged the implementation as exact commit
`52d563538daf049c7fa054c5c50cad05cf4b4bdf`. CI, CodeQL, and Dependency
Review each failed before executing a step because GitHub reported an account
payment or spending-limit block; the complete local gate above is therefore the
implementation evidence. The immutable upgrade plan installed exact build
`0.1.0+g52d563538daf`. Codex was refreshed to managed bundle
`0.1.0+codex.bd6f67d99b7d`, and ZCode was refreshed from the same launcher
identity. Both hosts are registered/enabled but runtime-unverified until a
fresh process loads them; current-profile Codex hook trust remains an attended
boundary and is not claimed by the isolated ordinary canary.

The first AR-200 canary, trial `ar200-52d5635-ordinary-01`, ended `NO-GO` at
trace `019fb0ed-b925-7622-9fcc-f8774f30110d`. It persisted two successful Luna
wrapper receipts and relevant proposals for eight units, including
`software-architect`, `section-508-accessibility-specialist`,
`python-application-engineer`, `typescript-application-engineer`,
`software-test-engineer`, `code-reviewer`,
`application-integration-verifier`, `test-results-analyzer`, and
`application-security-engineer`. The documentation unit nominated
`technical-writer` first, but its inferred amendment failed with the generic
amendment code. Atomic publication therefore yielded zero specialists,
delegations, accepted finalizations, header evidence, corrections, or files.

The bounded repair keeps selection inference-owned, binds amendment identity
to the exact inference-selected existing target, preserves authority and
context checks, and preserves every existing contract value before admitting
new values within the destination bounds. Amendment failures now report
content-free identity, authority/context, target-state, parent-prompt,
projection, reconstruction, additivity, coverage, or construction stages. The
curated gate now kills 7 of 7 mutations, including removal of amendment target
binding and restoration of unbounded additive outcomes, with zero survivors or
invalid results.

A provider-free reproduction against an owner-private copy of the live
272-worker store amended the actual `technical-writer` in place to revision 1,
kept the worker count at 272, rebound a deliberately different model-authored
slug to `technical-writer`, preserved every existing projected value, retained
all 12 employment outcomes, and bounded the workforce outcomes to 8 and scope
qualifiers to 4. The live store remained at revision 0 with the same hash.

Final repair verification passes: 111 focused tests with 1 skip and 1 expected
failure; 661 named-spine tests with 6 skips; 109 dashboard tests; every routing,
policy, delegation, CLI-startup, latency, and 263/1,000/10,000-agent scale gate;
537-document metadata and normal documentation validation; Ruff lint and
format; and Git diff checks. The final private-copy decision proof again kills
7 of 7 exact mutations with zero survivors or invalid results and leaves source
inputs unchanged.

## Approach

1. Split candidate validation into content-free, allowlisted stages and retain
   only stable reason codes in hiring and routing evidence.
2. Reproduce the remaining employment-to-workforce projection mismatch with a
   deterministic schema-valid candidate and repair only that confirmed edge.
3. Bind an inferred amendment to its chosen worker identity and merge contract
   fields additively within destination limits without changing online target
   selection or silently changing authority.
4. Add `agency eval decision-conformance`, which first proves a green baseline,
   copies the required source and tests into a private disposable directory,
   applies exact one-anchor mutations there, and requires the named test to fail
   normally for every mutation.
5. Curate mutations for the historical online-inference, role-ordering, and
   contractor-boundary regressions. A timeout, collection error, stale anchor,
   wrong failing test, or infrastructure error is invalid evidence, never a
   killed mutation.
6. Run focused review, the mutation proof, and the named fast production gate
   before merge, exact installation, and one bounded ordinary Codex canary.

## Dependencies

AR-119 and ADR-0088 own inference-first selection and the explicit offline
floor. AR-199 owns the ordinary Codex proof and its terminal trace. ADR-0112
owns atomic preflight evidence. ADR-0113 owns the isolated mutation-evidence
contract introduced here.

## Acceptance

- [x] Every post-parse contractor rejection records an allowlisted,
  content-free validation-stage code; no provider value or raw exception text
  enters the reason code.
- [x] A schema-valid employment contract whose routing prose reaches the
  employment text bound projects into the smaller workforce contract without a
  generic candidate failure while preserving the full governed employment
  contract in the compiled specialist prompt.
- [x] `agency eval decision-conformance --json` proves its baseline before
  mutation, operates only on a private disposable copy, rejects linked source
  inputs, and verifies its copied package and selected-test inputs remain
  byte-for-byte unchanged in the source checkout.
- [x] Curated mutations for configured-provider inference bypass, online role
  anchor reordering, contractor binding overflow, destination projection
  overflow, amendment identity drift, amendment destination overflow, and
  diagnostic collapse are all killed by their named focused tests.
- [x] An inferred amendment revises the exact selected existing worker, retains
  every pre-existing bounded contract value, and cannot silently change its
  authority or context mode.
- [x] Amendment rejection evidence identifies an allowlisted content-free
  stage without storing raw provider values or exception text.
- [x] A mutation counts as killed only when pytest exits with an ordinary test
  failure and the expected node fails; stale anchors, timeouts, collection
  failures, and unrelated failures make the gate fail.
- [x] Focused tests and the named fast Python, dashboard, routing,
  documentation, formatting, and diff gates pass on the exact source revision.
- [ ] The merged revision is installed exactly and one bounded ordinary Codex
  canary reports relevant specialist/model evidence, at least one completed
  specialist chain, one accepted finalization, and zero header corrections.
- [ ] The local shareable evidence page is updated with the exact prompt,
  selected and delegated agents, model receipts, correction count, mutation
  report, and scoped verdict.
