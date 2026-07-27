---
title: "AR-176: Align full-gate fixtures with hardened runtime contracts"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [testing, security, isolation, traceability, performance]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - agency_runtime/core/smoke.py
  - tests/test_adapter_parity.py
  - tests/test_coverage_final_delegation_private.py
  - tests/test_dashboard_service_coverage_complete_operations.py
  - tests/test_doctor.py
  - tests/test_executable_namespace_security.py
  - tests/test_owned_process_core_hardening.py
  - tests/test_roster_authority_gap_coverage_ar91.py
  - tests/test_roster_sync_gap_coverage_child.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-176
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-176: Align full-gate fixtures with hardened runtime contracts

## Problem

The first final warning-strict corpus passed 8,010 tests with 61 platform skips
and 1 expected failure, but failed 11 tests after 33 minutes 25 seconds. Focused
suites had hidden the failures because ten old tests no longer modeled current
configuration, executable-identity, filesystem-currentness, or immutable
authority contracts. One OpenClaw diagnostic also mislabeled a missing Node
executable as present but not runnable.

The monolithic process reached roughly 13 GB while retaining the complete test
session, so discovering stale low-level fixtures only at the end wastes local
time and would waste hosted budget if the same contract drift escaped fast
quality gates.

## Current state

Tests that require a file-owned Store identity opt out of the suite's synthetic
`AGENCY_DB_PATH`. Executable-discovery doubles accept the hardened
`current_directory` and `forbidden_roots` arguments; resolved-path fixtures
materialize the file that strict currentness requires. Candidate, snapshot, and
remediation fixtures carry immutable IDs, iterable SQLite-like cursors, current
active-basis evidence, and the current revision/count query shape.

The OpenClaw smoke path retains `skipped: node unavailable` for
`FileNotFoundError`; other launch-time `OSError` values remain visibly
`node not runnable`. Executable freezing and immediate revalidation are
unchanged.

## Approach

Preserve the hardened production contracts and repair each stale test at its
own boundary. Mark configuration-identity tests explicitly instead of deleting
the global isolation override. Make doubles accept and exercise security
arguments rather than weakening production call sites. Construct complete
authority rows so a test reaches the semantic rejection it claims to cover.

Keep the exact failed full run as evidence. Run all original node IDs together,
then one combined order-sensitive package of touched and neighboring files
before paying for the full corpus again.

## Dependencies

ADR-0027 requires truthful evidence diagnostics. ADR-0031 owns durable service
configuration identity. ADR-0055 requires frozen executable identity and
currentness. ADR-0066 owns append-only roster authority. ADR-0097 keeps the
expensive gate behind faster same-contract checks.

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Configuration-identity tests cannot inherit the suite's synthetic Store
  override accidentally.
- [x] Test doubles retain every executable namespace and forbidden-root
  argument used by production.
- [x] Strict resolved-path and authority fixtures provide current materialized
  identities instead of bypassing validation.
- [x] Missing and non-runnable Node diagnostics remain distinct without
  weakening launch identity checks.
- [x] All 11 original failures pass together.
- [x] Touched and neighboring files pass as one order-sensitive package: 670
  passed, 1 platform skip.
- [ ] The exact full warning-strict corpus passes from the implementation
  checkpoint.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

The exact failed command recorded 8,010 passed, 61 skipped, 1 expected failure,
and 11 failed in 33:25. After repair, the 11 original node IDs pass together in
1.53 seconds and the combined 12-file regression package passes 670 tests with
1 platform skip in 2:42. Ruff, format, and diff checks pass. A full rerun is
required before this issue can be locally complete.
