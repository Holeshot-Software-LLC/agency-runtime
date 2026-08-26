---
title: "Worklog detail: Restore expanded configuration regressions"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [testing, configuration, regression, release]
related:
  - docs/roadmap/issue-AR-294-restore-expanded-configuration-regressions.md
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - tests/test_configuration.py
  - tests/test_security_config_store_coverage_complete_configuration.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 257fe30fe7325485dcbef30195451309bdba63af
short: 257fe30f
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-294-restore-expanded-configuration-regressions.md
---

# Worklog detail: Restore expanded configuration regressions

## Purpose

Restore two stale expanded configuration tests exposed by the merged AR-293
verification run so the broader release signal is executable and trustworthy.

## Approach

Align the default-mode assertion with the canonical strict configuration and
assert all three stage budgets. Supply the required narrowing callback to the
low-level invalid-revision service test; the callback remains unreachable
because revision validation rejects the operation first.

## Challenges encountered

The named fast production spine excludes these broader configuration files, so
the drift appeared only after the candidate deliberately expanded its gate. The
pre-fix run was otherwise healthy: 1,125 passed and 21 skipped.

## Decisions and alternatives

Product defaults and the transaction signature were not weakened to satisfy
old tests. Both fixes are fixture-only alignments to current canonical behavior.

## Verification

- Both exact regressions failed before the correction and passed afterward.
- Focused Ruff lint/format, 827-file documentation validation, and diff checks
  passed.
- The full expanded merged spine is rerun after this clean checkpoint; its
  result must replace, not be inferred from, the pre-fix partial run.

## Follow-ups

- Record the full post-fix merged-spine result and proceed only if it is green.
- Create/link AR-294 only after explicit tracker authorization. No tag or
  release is authorized by this test correction.
