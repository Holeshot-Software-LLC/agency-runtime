---
title: "Worklog detail: Seal traced dashboard response contracts"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, traceability, security, performance, workforce]
related:
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-154-fail-malformed-initial-pages-closed.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
supersedes: []
superseded_by: null
type: worklog
commit: 6a3bdaa
short: 6a3bdaa
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-154-fail-malformed-initial-pages-closed.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
---

# Worklog detail: Seal traced dashboard response contracts

## Purpose

Close the final traced dashboard defects found by the production-readiness audit:
request identity reuse, cross-refresh races, client/server eligibility drift,
listener retention, incomplete or oversized evidence projections, and permissive
initial-page validation.

## Approach

The HTTP boundary now creates request-local identities even on persistent
connections and returns content-free protocol errors. Dashboard refreshes use
coordinated commit epochs and lifecycle-bound request scopes. Route Lab derives
eligibility from the same bounded host evidence as the server. Workforce and
hiring collection projections expose fixed metadata, retain exact governed
evidence behind explicit lookups, preserve one-read snapshots, and enforce
actual serialized response-byte budgets. The UI validates exact schemas and
evidence markers before committing state, and delegated listeners are installed
once and removed during teardown.

## Challenges encountered

Promotion readiness previously consumed full evidence references. The bounded
dashboard projection therefore derives only the strict qualification scalar in
SQLite, strips it from the public response, and feeds a private reconstruction
through the unchanged readiness policy. This preserves decision parity without
returning evidence documents or adding mutation authority.

## Decisions and alternatives

Collection completeness remains metadata-complete while large evidence stays
exact and operator-requested, consistent with ADR-0095. Truncating individual
evidence documents was rejected because it would silently corrupt governed
proof. Returning oversized internal payloads or budget details to clients was
also rejected; invariant failures are logged and exposed as generic HTTP 500s.

## Verification

- Root focused Python verification: 168 passed, 3 skipped.
- Root post-review regressions: 4 passed.
- Dashboard UI suite: 101 passed.
- Independent review: no runtime security, availability, transaction,
  promotion-authority, race, or accessibility blocker reproduced.
- Ruff check, Ruff format check, Python compilation, JavaScript syntax checks,
  and `git diff --check` passed.

## Follow-ups

The complete warning-strict release corpus, packaged-artifact smoke, and live
browser verification remain part of the production-readiness umbrella before
release claims are made.
