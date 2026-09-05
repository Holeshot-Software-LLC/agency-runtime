---
title: "AR-404: Complete the backlog through evidence-led delivery packages"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, review, acceptance, delivery]
related:
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
  - docs/roadmap/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-404
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
depends_on: [AR-400, AR-401, AR-402, AR-403]
blocks: []
---

# AR-404: Complete the backlog through evidence-led delivery packages

## Problem

The owner requested committed review artifacts, a plan covering the findings,
implementation, and backlog cleanup/completion. The first inventory found 155
unfinished records but only two existing acceptance files. Many entries already
describe implementation, others wait on native proof, and some still propose
behavior later decisions replaced. Treating all of them as new code fixes would
repeat work and risk reintroducing superseded behavior.

## Current state

Phase: implementing. The four independent review findings are implemented and merged
through PR #669. All-host deterministic smoke passes; one Claude native-child
canary passes on the installed build. Codex trust, OpenClaw restart permission
and Hermes/ZCode live-mode limitations are explicit, not successful live parity.

The linked inventory accounts for all 155 records at the delivery checkpoint;
it does not claim they have all been semantically reviewed. 105 are marked p0,
so dependency order and an observable outcome must drive packages. The strict
tracker audit identified three concrete bookkeeping actions: map the missing
AR-398 and AR-399 issues, and close verified AR-397. Existing historical
tracker exemptions are not permission to create duplicate issues.

Lane A now has twelve satisfied isolated acceptance verdicts. AR-397 (#654),
AR-398 (#670) and AR-399 (#671) are closed against their existing verified
records; the four accepted review issues close with the delivery-record PR.
The worklog registry supplies its merge identity and strict parity result.
After lane A, 151 baseline items remain unfinished, plus this coordination issue.

The next safety slice is not merely stale bookkeeping: a current offline
production-path replay at 1de05aea set strict_independence=true on the supported
legacy provider configuration, supplied valid creator/critic/security replies
from that same provider, and returned status=hired with a worker. The temporary
Store was discarded; no external model or production roster was used. AR-348
still has no production caller of enforce_strict_independence. AR-349's current
safety-repair exit still returns a rejected outcome without a hiring case, and
its existing regression explicitly asserts hiring_case is None. Reproduce and
fix these together with legacy, per-harness, fallback and safety-repair coverage.

## Approach

1. **Finish this review's delivery (lane A).** Persist exact installed evidence,
   obtain isolated acceptance verdicts for AR-400/401/402/403, merge records,
   close only accepted trackers. Keep platform/operator exits visible.
2. **Reconcile known record debt.** Bind AR-398 to #670 and AR-399 to #671,
   verify existing candidate-bound verdicts and close #654/#670/#671.
   The owner's 2026-09-05 backlog-cleanup request authorizes this bookkeeping;
   it does not authorize altering historical receipts or relaxing criteria.
3. **Security/hiring invariants first (lane B).** Start with AR-348 strict
   independence, AR-349 rejected-hire persistence, AR-350 risk hints versus
   binding verdicts, and AR-351 explicit-empty contracts. Reproduce the current
   boundary before changing it; AR-402/ADR-0217 changed domain semantics, so
   AR-351's domain proposal must be reconciled, not implemented blindly.
4. **Prove staffing quality and speed (lane C).** Use AR-253 as the performance
   owner, AR-370/374 for representative recall/eligibility, and AR-393 for gap
   accounting. Add a small fixed corpus of ordinary and true-gap tasks across
   native parent/child entry points; report end-to-end p50/p95, stage timings,
   calls/input counts, selected-role relevance, valid gap accounts and hiring
   outcomes. Compare cold/warm fresh processes and retain failed trials.
   Keep strict critics, audits and authority gates enabled. One recall pair
   cannot close this lane.
5. **Native completion (lane D).** Check exact installed identity, fresh process,
   trust and credential availability before spending live inference. AR-359's
   code is implemented but its specific operator-policy rewrite needs the exact
   approved text; AR-365/366/367/368/369/371 need their own host-visible evidence.
   Do not infer live success from deterministic adapters.
6. **Release and UI outcomes (lanes E/F).** Reconcile obsolete exhaustive-test
   requirements with current governance through explicit record changes, never
   by inventing a pass. Group remaining issues by their actual dependency and
   visible outcome; Windows/macOS evidence must come from those platforms.
7. **For every package:** cite current source/test evidence per criterion;
   implement missing behavior in an owned worktree; focused tests, at most two
   review passes, named fast spine, demo, isolated acceptance, PR merge and
   exact ledger. Only then update canonical and remote state. Duplicates or
   superseded proposals require a documented rationale and reciprocal links.

## Dependencies

The current review closes first. Native trust, service interruption, missing
approved operator text, platform availability, signing/publication and acceptance
changes remain explicit operator decisions. Broad cleanup does not bypass them.
No exhaustive workflow dispatch or unattended restart is implied.

## Acceptance

- [ ] Every unfinished item in the baseline inventory has a reviewed disposition: verified completion, a linked superseding/duplicate rationale, or a bounded remaining delivery package with explicit evidence and blockers.
- [ ] The current review findings and known AR-397/398/399 tracker debt have merged records, valid acceptance and strict tracker parity.
- [ ] Remaining packages are implemented and their applicable acceptance is satisfied before closure; no code, live-proof or operator gate is silently waived.
- [ ] The final inventory and canonical/remote statuses agree, with no unaccounted unfinished baseline item.

## Next bounded package

Complete lane A and the three explicit tracker reconciliations; then reproduce
AR-348/349 against current code and settle AR-393's historical-receipt criterion
with the owner. The full backlog remains open until the acceptance above is met.
