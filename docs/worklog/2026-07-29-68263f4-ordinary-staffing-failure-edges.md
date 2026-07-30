---
title: "Worklog detail: Repair ordinary staffing failure edges"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [workforce, hiring, receipts, codex, skills]
related:
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 68263f4
short: 68263f4
date: 2026-07-29
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/173
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Repair ordinary staffing failure edges

## Purpose

Repair the first failed plan-to-binding edge from exact-installed ordinary
trace `019fb064-6448-7853-955e-ad6896f3040b` and make any remaining staffing
gap durably traceable without granting deterministic code selection authority.

## Approach

Dynamic hiring now treats the employment schema and the compiled workforce
schema as distinct bounded contracts. Exact causing-unit facts are prepended
and capped at the employment boundary; compiled outcomes, taxonomy values, and
scope qualifiers are capped again at their smaller destination limits. The
generated control skill describes only its three exact accepted messages, so
ordinary work cannot discover it as a broad inspection skill. Routing receipts
now preserve bounded per-unit inference nominations, verifier-safe proposals,
and reason families while discarding free-form evidence and prompt content.

## Challenges encountered

The live hiring failure appeared only when a provider returned the maximum 12
items allowed by its schema. Binding one exact unit fact produced 13 items and
the contractor reparse rejected its own valid response. Fixing only that edge
would have exposed the next mismatch because the workforce contract accepts at
most eight outcomes/taxonomy items and four qualifiers.

## Decisions and alternatives

Preserve unit facts first rather than truncating the newly bound evidence.
Project trace metadata instead of storing full recruiter evidence. Do not add
anchors, deterministic substitutes, or other online selection authority; the
configured provider remains the worker selector and the verifier remains a
safety veto.

## Verification

- Broadened focused suite: 134 passed, 1 skipped, 1 expected xfail.
- Named fast Python spine: 654 passed, 6 skipped.
- Dashboard suite: 109 passed.
- Routing evaluation: every gate passed.
- Documentation, Ruff, formatting, and diff checks passed.

## Follow-ups

Merge and exact-install the repair, then run AR-199's final bounded ordinary
isolated-profile product proof. A failure closes the package as an exact
`NO-GO` rather than opening another repair loop.
