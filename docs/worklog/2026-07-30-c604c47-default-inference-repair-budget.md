---
title: "Worklog detail: Fund the default inference repair"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, configuration, budgets, mutation-testing]
related:
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c604c47
short: c604c47
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
---

# Worklog detail: Fund the default inference repair

## Purpose

Make the configured fast-mode default capable of executing its advertised one
bounded semantic repair after the mandatory planner and recruiter calls. The
change follows terminal AR-200 trace `019fb31f-5da6-7dd0-a983-9b983f767b9f`,
which exhausted an installed two-call budget immediately after recruiter
contract rejection.

## Approach

Align bundled YAML, typed dataclass, raw loader, and partial-document validation
at a three-call fresh default. Preserve any explicit persisted lower value as an
operator-owned cap. Prove the exact planner, rejected recruiter, repaired
recruiter sequence; verify the generated host timeout; and add a curated private
mutation that lowers the typed default back to two.

## Challenges encountered

The repository had three conflicting behaviors: bundled fresh configuration
declared one call, the Python default declared two, and the live profile
persisted two. Enabling the third call also exposed a safety fixture that only
supplied two mocked responses; it now supplies a second invalid recruiter reply
and proves Agency abstains after the bounded repair instead of appointing a
disabled worker. Review also corrected delivery ordering so the local explicit
budget is changed before host bundles calculate their timeout.

## Decisions and alternatives

[ADR-0114](../decisions/0114-fund-one-default-workforce-semantic-repair.md)
keeps the configured call budget as a real upper bound. It rejects spending a
hidden retry outside the cap, deterministic invention of a missing staffing
decision, and silent migration of explicit lower budgets.

## Verification

- The exact production-sequence regression failed first with
  `workforce_call_budget_exhausted` after two calls.
- Focused inference, configuration, installer, and conformance suite: 234
  passed, 1 skipped.
- Decision conformance: green baseline; 10/10 mutations killed; zero survivors
  or invalid results; source inputs unchanged.
- Documentation metadata and policy checks passed; normal validation passed for
  541 Markdown files.
- Focused Ruff lint and format checks passed; Git diff check passed.

## Follow-ups

Run the named fast production gate, merge and install the exact tool revision,
set the local explicit budget to three before refreshing Codex and ZCode, and
run one bounded AR-201 ordinary canary.
