---
title: "Worklog detail: docs(production): record fresh artifact and live evidence"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [production-readiness, artifacts, routing, ui, dogfood]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: worklog
commit: 99b51bd
short: 99b51bd
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
---

# Worklog detail: docs(production): record fresh artifact and live evidence

## Purpose

Replace source-only readiness claims with exact `19b20bed` package/install,
Codex freshness, live routing, and current authenticated dashboard evidence.

## Approach

Build and verify exact `19b20bed` Windows artifacts in a trusted private root;
install wheel and sdist into separate fresh Python runtimes; audit each Codex
integration layer independently; exercise the dashboard and bounded live routes;
then preserve both the pre-fix defect and post-fix fail-closed confirmation.

## Challenges encountered

The release builder correctly rejected the dirty checkout, system Temp ACL, and
repository-venv ACL. The normal-profile Codex integration is internally intact
but stale and cannot be safely refreshed because AR-143 still lacks a positive
installation operator-presence path.

## Decisions and alternatives

The report keeps production at NO-GO. A current-source foreground dashboard is
demo-quality, but it is not substituted for an installed, activation-verified
Codex runtime. No recommendation is promoted to activation or execution.

## Verification

- Strict Windows wheel/sdist build, independent distribution verification, and
  separate fresh Python 3.10 package smokes passed.
- The later AR-179 code repair deliberately leaves a final current-head rebuild
  open; the earlier bytes are not promoted to current-release evidence.
- All dashboard sections, refresh, authenticated Route Lab, and browser console
  smoke passed with zero console warnings/errors.
- Post-fix regulated-assurance route abstained with zero selections and exact
  provider/model receipts.
- Documentation validation passed for 447 Markdown files; issue #154 closed.

## Follow-ups

Complete the AR-143/161 attended install path, Linux portable artifact evidence,
five live host canaries, and the explicitly requested manual integration gates.
