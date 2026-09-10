---
title: "Investigate Hermes ordinary-review assurance"
status: active
category: worklog
created: 2026-09-10
updated: 2026-09-10
tags: [hermes, reliability, evidence]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-10
pr: null
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
routing, Ruff788 and documentation checks pass. Private conformance and one
fresh native observation are pending. All651 retained Hermes projection files
match the manifest. Planner/recruiter source and Hermes adapter match47241e5e;
this is the retained recipe21 projection, not Codex's recipe22 refresh.

## Follow-ups

Complete the bounded fresh ordinary-review diagnostic with pass-through capture
of its own recruiter and critic packets, then record exact terminal evidence.
AR-418 upstream PR106490 remains OPEN at30f421ecce; actual Hermes checkout
remains clean7cd91114. Adoption and original provider-cap proof remain unproven.
AR-404/418/430 stay open; Zcode remains deferred. No exhaustive or Windows run.
