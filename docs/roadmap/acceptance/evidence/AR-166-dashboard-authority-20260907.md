---
title: "AR-166 current dashboard authority and disclosure evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, security, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-166 current dashboard authority and disclosure evidence

## Reproduction and repair

Baseline main 520a10e36893977101494193852f370968f05cd2; merge ledger
44c94c925f815cc18aefb1299f856cd19c844228. Against the unchanged renderer, the
updated key-redaction test and new two-provider interaction test both fail:
expected selector.disabled=false, actual true. The focused Node command with
name pattern 'provider configuration without|provider secret selector follows'
returns exit 1, zero passes/two failures, 62.333575 ms.

The sole product edit changes the nonempty-list assignment from true to false.
Empty/non-array/unparseable lists still disable it. The new test selects index 1,
preserves it through re-render, and stages only a providers.1.api_key secret
operation. Four invalid/empty states and stale-selection recovery are covered.
Stored keys never enter the JSON control. The test allows no fetch or persistence.

## Fresh verification

Linux, checkout-local Python imports, no new skips/xfails or lowered thresholds:

- Full UI: 189 passes, no skips/failures, 240.844917 ms.
- Production UI coverage: 96.93 percent lines, 86.71 branches, 95.71 functions;
  unchanged 95/86/93 thresholds and dashboard-JavaScript-only scope.
- Warning-strict test_dashboard_auth_boundary_regression,
  test_dashboard_transaction_refactors, test_cli_owner_authority,
  test_workforce_cli and test_dashboard: 235 passes, no skips/failures, 46.37s.
- Fresh named production spine: 1085 passes/three existing skips, 67.88s.
- Ruff check/format: 766 files pass. Scoped diff check passes.

UUIDv4 validation, safe errors, exact response correlation, validated Route Lab
IDs, runtime-capture privacy labels and Store-backed definition provenance
remain. No backend, authentication, broker policy, retention or capture setting
changed. These tests are not native-host or real-provider staffing evidence.

## Requirement reconciliation

ADR-0229 explicitly changes only criterion 1 under accepted ADR-0117.
Original wording remains in the canonical issue; the other five are unchanged.
AR-298's current bounded definition is at most 262144 characters, not the
historical 8192-character preview. Stored definition is not runtime capture or
delivery proof. The governed legacy tracker exemption applies while unmapped.

## Browser checkpoint

The focused source-served browser interaction is the next bounded check.
No installed-wheel, native Windows, attended-host or full accessibility claim.
The builder records observations, never acceptance verdicts.

## Publication validation

Fresh metadata and strict docs with required trackers pass for 1188 Markdown
files. Strict tracker passes for 397 mapped records with two historical
PR-tracked exceptions. Policy availability is current; the exact worklog
indexes 1985 substantive commits before this repair. Diff check returns zero.
AR-166 is governed pre-tracker history, not an unrecorded remote closure.
