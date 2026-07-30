---
title: "AR-200: Make workforce decisions diagnosable and mutation-conformant"
status: in_progress
category: roadmap
created: 2026-07-29
updated: 2026-07-30
tags: [workforce, hiring, diagnostics, mutation-testing, inference, routing]
related:
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/handoffs/issue-AR-200.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-200
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/175
depends_on: [AR-119, AR-199, AR-201]
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

PR 177 merged the bounded amendment repair as exact main revision
`8bb504ce3c76aca6f1a243750d90419c1375be08`. Its CI, CodeQL, and Dependency
Review jobs were again refused before repository steps by the same GitHub
account-payment or spending-limit condition, so the complete local gate remains
the executable evidence. The immutable ref upgrade installed exact build
`0.1.0+g8bb504ce3c76`; Codex was refreshed to managed bundle
`0.1.0+codex.d6240568ca33` and ZCode was refreshed from the same launcher. Both
hosts are registered and enabled. Current-profile Codex activation remains an
attended fresh-process boundary, separate from the isolated product canary.

The one final bounded canary, trial `ar200-8bb504c-ordinary-02`, is terminal
`NO-GO` at trace `019fb121-2e4c-70e0-a286-7fe25fc2e5ba`. Codex completed
with exit 0 in 162.641 seconds and the isolated plugin recorded a native host
contract plus two successful `gpt-5.6-luna` wrapper receipts. Seven of nine
units had relevant verifier-safe proposals, but architecture and documentation
remained empty. Architecture consumed the one hiring call and abstained with
`gap_not_proven`; documentation was then `task_hiring_limit_reached`.
Atomic publication recorded zero selected, loaded, or delegated specialists.
The Stop path recorded `continue` for `evidence_verification` and then
`retry_exhausted`; all seven header fields were absent, correction count was
null rather than zero, and the empty workspace failed all five product checks.
The local evidence page records the exact prompt, staffing receipt, model and
finalization evidence, mutation report, and scoped verdict.

The bounded follow-up identified a decision-provenance defect rather than a
missing architecture specialist. Nomination output classified candidates but
did not say whether inference intended to staff the unit or declare a gap. Any
structurally valid nomination that the typed verifier could not assemble was
therefore relabeled as `no_safe_sufficient_team` and admitted to hiring. A
declined hiring analysis then counted against `max_hires_per_task`, starving
the next declared unit even though no workforce change occurred.

The repair requires inference to return `decision: staff|gap` for every unit.
A staff decision without a safe typed team, or a gap decision with one, gets one
bounded semantic repair from the same provider. Only an explicit gap carrying
the verifier's closed safe reason set reaches independent hiring analysis.
Hiring decline stages are now distinct and content-free, and only an applied
hire or amendment spends the per-task allowance. Two bounded review passes are
complete. The focused suite passes 121 tests with 1 skip; the named Python
production spine passes 664 with 6 skips; dashboard UI passes 109; all routing,
policy, delegation, latency, startup, and 263/1,000/10,000-worker scale gates
pass; and 538 Markdown files validate. The final isolated evaluator has a green
baseline and kills all 9 curated mutations with zero survivors or invalid
results while leaving source inputs unchanged.

PR 179 merged that repair as exact main revision
`57c34e609dec06b15b73ceacdd6ee8cf75c94e95`. The immutable install reports
build `0.1.0+g57c34e609dec`; Codex refresh install
`7a0a5b57-4d8b-47d1-afd3-166803f7f871` generated bundle
`0.1.0+codex.8bff77d9195e`, and ZCode refresh install
`262e7e8c-4698-4e1c-8795-32cb0e8e852d` used the same source identity. No trust
prompt blocked either refresh.

The one new ordinary canary, trial `ar200-57c34e6-ordinary-03`, is terminal
`NO-GO` at trace `019fb31f-5da6-7dd0-a983-9b983f767b9f`. The planner applied
through the configured Luna wrapper, but the recruiter response failed its
explicit decision contract. Planning and the rejected recruiter consumed the
installed two-call fast budget, so the bounded recruiter repair never ran and
the route stopped with `workforce_call_budget_exhausted`. It recorded zero
selected, loaded, or delegated specialists; zero native spawn/wait events; no
accepted finalization; zero artifacts; and five failed product checks. All
seven header fields were structurally present on the first response, but that
header is not specialist activity proof and correction count was unavailable.

AR-201 records the bounded follow-up. Fresh defaults must fund planner,
recruiter, and one semantic repair while preserving explicit lower budgets as
operator-owned opt-outs. AR-200 remains open until the later ordinary canary
proves the full workforce and delegation chain.

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
7. Require explicit inference-owned `staff` / `gap` decisions and send semantic
   contradictions through the existing bounded repair path rather than
   manufacturing a deterministic gap.
8. Count only applied workforce changes against `max_hires_per_task`; keep each
   declared unit single-attempt and the provider call budget independently
   bounded.

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
- [x] Every configured-provider nomination explicitly says `staff` or `gap`;
  contradictory typed evidence receives one bounded inference repair and is
  never silently reclassified by deterministic code.
- [x] Only an inference-declared gap with the verifier's safe no-team reason
  closure enters hiring, and hiring decline stages remain content-free.
- [x] A declined hiring analysis does not consume `max_hires_per_task` or starve
  a later declared gap; the corresponding reversal is killed by the curated
  mutation gate.
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
- [x] The merged revision is installed exactly for Codex and ZCode.
- [ ] One bounded ordinary Codex canary reports relevant specialist/model
  evidence, at least one completed specialist chain, one accepted finalization,
  and zero header corrections. The terminal AR-200 canary did not satisfy this.
- [x] The local shareable evidence page is updated with the exact prompt,
  selected and delegated agents, model receipts, correction count, mutation
  report, and scoped verdict.
