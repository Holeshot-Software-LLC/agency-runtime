---
title: "Worklog: remove copied current schema literals"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, testing, store]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: worklog
commit: 11371cb6a14d91ebe998ea249f8c5545f49e5705
short: 11371cb6
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/683
related_issues:
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog: remove copied current schema literals

## Purpose

Verify whether old agent-authored work is still relevant. AR-148's malformed
signature repair already exists. Wider validation instead reproduced AR-323's
stale schema-version test coupling, now also present in seven related migration
and credential-redaction cases. Use the existing issue for the same defect.

## Approach

Compare materialized current schemas with the already-imported SCHEMA_VERSION,
not a second copied 46 literal. Keep every historical input version, exact
column/index/trigger/row assertion, credential-redaction check and ledger
one-use invariant. No production schema or migration implementation changes.

## Challenges encountered

Before the fix, the six-file Store/schema/release expansion failed seven tests
and passed 364; the native-child ledger file failed three and passed 27. All ten
failures were stale current-output literals, not failed behavioral assertions.
The resulting seven-file package passes 401 tests in 24.47 seconds.

## Decisions and alternatives

Do not roll production schema 49 back to an old test expectation, or copy 49
into each assertion and recreate the same future failure. Preserve explicit
old migration inputs because those are meaningful regression coverage.
AR-347 already exempts AR-323 as pre-tracker history; retain its original
future-tracker criterion as history and reconcile only that administrative
condition, without changing the allow-list or weakening its validator.

## Verification

- Seven-file focused package: 401 passed, warnings strict.
- Fresh named production spine: 1030 passed, three existing skips in 63.73s.
- Ruff passes; 764 Python files already formatted.
- Strict docs and metadata pass for 1101 Markdown files before this detail.
- AR-148/323 builder evidence is pending isolated acceptance, not yet done.
- No exhaustive corpus, native Windows proof or new artifact installation.
  Product source remains identical to the previously accepted installed build.

## Follow-ups

Freeze AR-148/323 evidence to this candidate, obtain isolated criterion verdicts,
and close only if satisfied. AR-406's separate current UI function-coverage
failure remains open; no passing claim is inferred from these Python tests.
