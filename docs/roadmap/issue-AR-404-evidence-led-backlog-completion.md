---
title: "AR-404: Complete the backlog through evidence-led delivery packages"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, review, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
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

Owner clarification: work sequentially, close verified completed records,
assess agent-written tickets against the current product rather than accepting
their proposed designs, and leave Windows-specific work to the owner's machine.
The starting 147 count was 43 open trackers plus 104 unfinished pre-tracker
local records, not 147 demonstrated defects. The count reconciliation records
the exact join. AR-149 is already implemented and now has current real HTTP
verification; all four isolated criteria are satisfied and the record is done.
The first absent 2/3 verdicts remain in f2e41b89; the targeted second check
followed missing ContextVar/Store source citations, not criterion changes.
AR-139 is retired:
AR-295 and 3023f0557 superseded its old ceiling with audited required UI;
current 386,366-byte assets pass the strict 378 KiB guard. No guard is changed.
AR-152's listener soak passes,
but the separate current UI function-coverage gate fails (91.12 versus 93
percent), recorded as AR-406/#682. Filing it adds one tracked issue; retiring
AR-139 and completing AR-149 remove two legacy items (44 tracked plus 102
unfinished legacy). No corresponding external trackers exist for those two.

AR-148's signature repair is also present. Its wider validation uncovered the
already-tracked AR-323 stale schema-literal defect: three native-child ledger
cases and seven migration/credential tests expected 46 while schema is 49.
The test-only correction removes copied current-version literals, preserves
historical input versions and all behavioral assertions, and passes the complete
401-test focused package. Fresh named production spine: 1030 passed, three
existing skips (63.73s). AR-148/323 builder records await isolated verification;
no new tracker was created for this existing issue family.

A stale-hook warning prompted `agency install --agent codex` from the existing
installed immutable runtime. Codex files refreshed; exit 1 honestly retains
activation-required/unverified hook trust. A fresh attended local Codex terminal
must grant hook trust; no trust bypass or repeated unattended retry occurred.

Phase: implementing. The owner asked to push and continue after the first
semantic record cleanup. That cleanup is on main through PR #676/#677 at
3ed51069. Two bounded defect packages follow it:

- AR-405 is done and merged through PR #678 at 78e501b7; tracker #675 is closed.
  Its test-only correction turns 91 pass/two fail into 100 pass/one native
  Windows skip, without changing production identity semantics. Three isolated
  criteria are satisfied; portable real and synthetic assertions remain active.
- AR-271 is done for its bounded contract outcome; PR #679 merged at 5434836e.
  Install and uninstall now share the exact bounded stopped-state classifier.
  Regression-first seven fail/fifteen pass becomes a 248-pass focused suite
  with two native Windows skips. Owner denial, execution-identity drift and
  live/unknown state after approval and before commit remain blocking.
  Three isolated criteria are satisfied; fast spine 1030 pass/three skips,
  UI 138, docs/acceptance/tracker tests 104, routing and protected conformance
  baseline plus 182 mutation kills pass. Exact merged-main non-editable install
  and all eight deterministic smoke checks pass, covering five host contracts.
  Native refresh remains partial: Codex needs attended hook trust and OpenClaw
  is live. Claude/Hermes/ZCode registered/enabled, but no current-build live
  session is claimed. The installer restarted its dashboard and repaired
  fourteen Claude package permissions under recorded consent; no OpenClaw
  stop/restart/uninstall or credential change occurred.

Prior delivery accounting: 146 unfinished baseline records plus AR-404 (147 then-current
unfinished records). The frozen inventory started with 155, the four accepted
AR-400..403 fixes left 151, and four obsolete policies AR-132/167/169/267 left
147. AR-271 removes one more baseline item; AR-405 was filed outside that
baseline and has since closed. The first semantic review and historical
checkpoint counts remain in the linked disposition record.

AR-160 retains current paired no-helper release artifact proof under ADR-0219.
AR-285 remains in_progress with three satisfied and two absent criteria:
trusted-runner wiring citations and a successful changed-precondition dry-run
receipt. Its real historical installs do not fill both evidence gaps. Do not
conflate its receipt-specific acceptance with AR-271's new bounded contract.

Earlier lane A has twelve satisfied isolated verdicts for AR-400..403, merged
through PR #669 at 1de05aea. AR-397/398/399 tracker debt is reconciled at
#654/#670/#671. That immutable runtime's deterministic five-host smoke and
one Claude native-child pass remain scoped to that build; Codex trust,
OpenClaw restart consent and Hermes/ZCode ordinary-session proof remain visible.

The review still does not support mass closure. AR-348 permits same-provider
creator/reviewer hiring despite strict_independence=true in a current offline
production-path replay; AR-349 still returns repair exhaustion without a durable
rejected case. AR-350 needs an explicit authority decision. AR-337's literal
all-supported-host wording disagrees with its four-host battery, and AR-351's
domain-axis proposal conflicts with descriptive-domain semantics. These remain
bounded packages, not assumptions that old checkboxes or inherited p0 labels
are authoritative.

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
approved operator text, platform availability and publication remain explicit
operator decisions. The current owner-requested cleanup reconciles obsolete
criteria through cited successor decisions; ADR-0219 retires only the removed
helper's signing obligations. Broad cleanup does not waive current proof gates.
No exhaustive workflow dispatch or unattended restart is implied.

## Acceptance

- [ ] Every unfinished item in the baseline inventory has a reviewed disposition: verified completion, a linked superseding/duplicate rationale, or a bounded remaining delivery package with explicit evidence and blockers.
- [ ] The current review findings and known AR-397/398/399 tracker debt have merged records, valid acceptance and strict tracker parity.
- [ ] Remaining packages are implemented and their applicable acceptance is satisfied before closure; no code, live-proof or operator gate is silently waived.
- [ ] The final inventory and canonical/remote statuses agree, with no unaccounted unfinished baseline item.

## Next bounded package

AR-149 is accepted and AR-139's obsolete ceiling is retired. Reconcile
historical record relevance one by one, first completing AR-148/323 isolated
acceptance, then AR-152's listener behavior; keep AR-406's current
shared coverage failure visible. Then verify AR-298 and deliver genuine
AR-348/349 hiring-safety fixes. Do not do Windows-specific work. AR-271 and
AR-405 have their own satisfied acceptance; AR-285 still needs its two named
evidence gaps, not a repeated classifier test. The full backlog remains open
until every baseline record has a reviewed disposition and remaining
acceptance is met.
