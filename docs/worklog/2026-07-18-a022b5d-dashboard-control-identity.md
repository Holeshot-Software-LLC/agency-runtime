---
title: "Worklog detail: Validate installed dashboard control identity"
status: active
category: worklog
created: 2026-07-18
updated: 2026-07-18
tags: [dashboard, service, windows, security, diagnostics]
related:
  - docs/roadmap/README.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
supersedes: []
superseded_by: null
type: worklog
commit: a022b5dc2e3a32feccdeac520f2a90ae29cc0cb8
short: a022b5d
date: 2026-07-18
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-98-validate-dashboard-service-launcher-status.md
  - docs/roadmap/issue-AR-99-dashboard-broker-materialized-master-control.md
---

# Worklog detail: Validate installed dashboard control identity

## Purpose

Correct two defects found only after installing the verified artifact into the
real Windows Codex profile: a healthy dashboard service falsely recommended
repair, and its authenticated global-control broker became unusable after the
first toggle materialized the master document.

## Approach

Status and open recovery now run the existing read-only launcher identity
validator before evaluating a schema-v2 service manifest. The authenticated
dashboard handler reads its immutable server-bound master path through the
strict owner-side validator. Restricted host consumers continue to use the
reduced-privilege, fail-enabled reader and cannot manufacture disabled state.

## Challenges encountered

The service remained active, reachable, and definition-current while reporting
`manifest_current: false`, which initially resembled installation drift.
Separately, the first global toggle could succeed from a restricted process
because no control document existed; only the second transition exposed that
the LeastPrivilege service was incorrectly using a reader designed for
non-mutating sandbox consumers.

## Decisions and alternatives

Weakening the restricted reader was rejected because its inability to consume a
mutable path prevents a sandbox from forging disabled state. The correction is
limited to the authenticated broker, which already owns compare-and-swap write
authority and still validates owner-private ACLs, path identity, links, bounded
schema, generation, confirmation, and transition receipts.

## Verification

- Dashboard service status/open-recovery regressions: 78 passed.
- Dashboard, master-bypass, and restricted broker regressions: 297 passed.
- Independent security review approved the boundary and found no weakened control.
- Ruff check, Ruff format, documentation validation, tracker mapping, and diff checks passed.

## Follow-ups

Rebuild the committed artifacts, reinstall them into Codex, repeat global
off/on and per-agent controls, verify the live dashboard in a browser, and
obtain hosted Windows/Linux CI before tracker closure.
