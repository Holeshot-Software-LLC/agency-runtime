---
title: "Investigate Hermes ordinary-review assurance"
status: active
category: worklog
created: 2026-09-10
updated: 2026-09-10
tags: [hermes, reliability, evidence]
related:
  - docs/roadmap/issue-AR-432-preserve-numeric-facts-in-review-plans.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
supersedes: []
superseded_by: null
type: worklog
commit: 2a5663152f6a6c916596fa92b5c7ba8c902b5745
short: 2a566315
date: 2026-09-10
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/844
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Investigate Hermes ordinary-review assurance

## Purpose

Determine whether the exact ordinary-review assurance veto justifies a repair,
while preserving the old receipt and AR-418's separate upstream and truncation gates.
Fresh Agency MCP status succeeds in this parent: verified SQLite binding,
293 roster entries. The earlier parent's closed transport is separate.

## Approach

Read-only queries bind session20260909_113727_2e00b0 and trace ending e03a9447
to preflight_failed, sequence1670. The failure receipt retains applied planner,
recruiter and critic stages and staffing_critic_rejected with
critic_missing_independent_review_assurance. Zero routing_decisions,
routing_intent, specialists_loaded, model_receipts and finalization_events rows
are retained for that trace; preflight_result is empty. Native session message
inventory contains no critic packet. Retained logs do not recover the proposal.
Exact run/failure hashes and the query inventory are in
AR-404-original-assurance-audit-20260910.json under roadmap evidence.

The historical2b19cce6 critic contract already limits assurance vetoes to work
called for by the plan and excludes completed-task evidence. The model's reason
code alone cannot tell whether its rejected team lacked required assurance.
Historical critic correctness is therefore indeterminate. No product repair is
supported by these records; no critic, validator, staffing or trust rule changes.

## Challenges encountered

The first routing check used a nonexistent package module entry point; the
correct CLI entry point succeeds. A system-Python docs check lacked the package
on its import path; the test environment with explicit repository path passes.
The first conformance baseline hit the previously documented default-umask
private-directory fixture failure before mutation. Its output is retained;
one corrected run uses077, without altering trust policy. These are local
verification invocation failures, not new native receipts.

## Decisions and alternatives

Retain the historical failure and its missing evidence instead of reconstructing
an alleged historical plan from fresh inference. A single fresh exact-request
native observation may establish current behavior; it cannot determine the
original critic's correctness. Existing ADR-0200 governs this evidence boundary.
No new product decision or issue closure is made.

## Verification

Focused critic17passed; named production1151passed/3skipped; UI224passed;
routing, Ruff788 and documentation checks pass. Private conformance passes188/188 with zero survivors and unchanged source.
The fresh native observation completed; exact results are below. All651 retained Hermes projection files
match the manifest. Planner/recruiter source and Hermes adapter match47241e5e;
this is the retained recipe21 projection, not Codex's recipe22 refresh.

## Follow-ups

AR-432 tracks the separately observed incorrect numeric fact in the accepted
plan. The bounded historical assurance investigation and fresh diagnostic are
complete; neither repairs nor relabels the original failed receipt.
AR-418 upstream PR106490 remains OPEN at30f421ecce; actual Hermes checkout
remains clean7cd91114. Adoption and original provider-cap proof remain unproven.
AR-404/418/430 stay open; Zcode remains deferred. No exhaustive or Windows run.

## Demo-ready checkpoint

Private077 conformance passes188/188 in341.533s. All required pre-demo checks
are complete, with the prior invocation failures preserved. PR844 carries this
records-only package. The clean substantive/ledger pair precedes one bounded
native ordinary-review observation; no installation or trust refresh is needed.

## Fresh native result

One exact ordinary_review invocation completed in86.235s, exit0, no timeout:
session20260910_081128_6d1bcd, trace
20260910_081128_6d1bcd:861485c1-b4aa-416f-bcbf-3d6c8332c8e7:df76d074.
All provider stages applied; the captured critic approved with no reason codes.
The plan retains analysis and a dependent independent static-review unit, with
separate context identifiers. Its one selected code-reviewer card is present
in full2379characters in native model-facing input. All five Store headers and
authoritative final hashdd9b5b8ce1ec1e61d86599c01d1cf20878eec1c7c48d0f2c48b0952314818ef9
match native bytes. No delegated execution or test execution is claimed.
The CLI toolset warning is preserved in stdout; the actual native assistant
message supplies the authoritative response hash.

Both recruiter and critic packets were captured without changing bytes; the
observer recorded no errors and restored configuration byte-for-byte. The first
observer launcher stopped at import before configuration mutation or a native
invocation; correcting that helper import started the sole native attempt.
Original run/failure hashes still match after collection. The original critic's
correctness remains indeterminate, irrespective of this fresh success.

## Separate factual finding

The accepted plan's unit-defect-analysis says the expected mean of[1.0,2.0]
is2.5. The native final correctly says1.5. Both captured packets preserve the
bad plan value; the raw planner transport response is unavailable, so this does
not establish where it entered the plan. AR-432/#845 records that bounded
follow-up. A staffing critic's approval is not a mathematical-answer certificate.
Do not broaden this package into a speculative planner repair or an all-host pass.

## Delivery scope

The scoped investigation and single fresh native diagnostic reached live_demo.
PR844 carries records only. AR-404/418/430/432 remain open; AR-431 remains closed.
No installation, trust, selector, critic, validator or source behavior changed.
OpenClaw full-card visibility remains unobserved in the prior successful
review/follow-up; preserve owner order and Zcode deferral for the next package.

## Merge record

PR844 merged atc216d31d884ec795180c8c2a6a4e949afc64c664 on2026-09-10,
with exact subject `docs: merge PR844 Hermes ordinary-review assurance evidence`.
The source worktree is historical. The merge-ledger worktree records this
substantive merge and its reciprocal roadmap commit cell. The scoped evidence
package is complete; AR-404/418/430/432 remain open and no failed receipt was
reopened. Strict tracker parity covers423roadmap items, with two historical
PR-tracked exceptions. No all-host, planner-fact repair or truncation acceptance.
