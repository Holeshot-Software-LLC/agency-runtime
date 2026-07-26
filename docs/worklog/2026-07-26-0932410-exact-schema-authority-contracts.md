---
title: "Worklog: Enforce exact schema authority contracts"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [security, sqlite, schema, remediation, workforce]
related:
  - docs/roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
supersedes: []
superseded_by: null
type: worklog
commit: 093241033300da2347baa898728ef89f6f5df92f
short: 0932410
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
---

# Worklog: Enforce exact schema authority contracts

## Purpose

Prevent weakened same-name SQLite objects from being accepted as production
current and make malformed remediation signatures fail closed without raising.

## Approach

Promoted activation-consumption DDL and workforce authority objects to
canonical definitions. Currentness now compares complete normalized SQL, with a
scanner that ignores syntax whitespace and keyword case outside quotes while
preserving every quoted literal and identifier byte. Exact legacy consumption
DDL remains the only migration input; unknown shapes stop initialization.
Remediation signature verification now admits only exact lowercase SHA-256 hex
before constant-time comparison.

## Challenges encountered

Name and substring checks proved insufficient because an attacker or damaged
migration could retain expected names while removing primary, uniqueness,
foreign-key, immutability, or lineage requirements. The prior normalizer also
erased a semantic distinction inside SQL string literals.

## Decisions and alternatives

ADR-0012 remains the governing durable-store contract. Semantic spot checks
were rejected because they leave unenumerated constraints and trigger bodies
outside currentness. Broad repair of an unknown constrained table was rejected
because copying evidence through an unrecognized authority shape could bless
corrupt state.

## Verification

- Focused schema and HMAC package: 58 passed.
- Broader Store/schema/roster/workforce package: 434 passed, 2 skipped.
- Ruff check and format check: passed.
- Documentation and diff validation: passed.

## Follow-ups

The complete integrated Python, coverage, performance, and release gates remain
required. Tracker creation for AR-134 and AR-148 remains pending explicit
authorization.
