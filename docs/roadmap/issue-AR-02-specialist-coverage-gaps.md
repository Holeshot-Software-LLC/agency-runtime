---
title: "AR-02: Close specialist coverage gaps"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-18
tags: [roster, policy]
related:
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0033-explicit-companion-route-availability.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-02
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/2"
depends_on: []
blocks: [AR-83, AR-86]
---

# AR-02: Close specialist coverage gaps

## Problem

The bundled companion policy contains conditional routes to specialist slugs that are not present in the active starter roster. Those branches cannot resolve when a user relies only on repository-provided data.

## Current state

The starter roster now includes governed, versioned definitions for
`internationalization-engineer`, `payments-billing-engineer`, and
`test-automation-engineer`. The bundled policy classifies all 238 referenced
specialists: seven are required bundled specialists and 231 are roster-gated.
A roster-gated route is skipped with an explicit reason until an approved
active roster supplies the specialist.

## Approach

Keep specialist definitions in-repository when they are required for the
starter experience. Generate the explicit availability registry from every
action and division route, validate it against the active roster, and fail the
policy command when a required or unclassified route cannot resolve. Preserve
the extended policy by enabling roster-gated specialists after governed
activation rather than deleting their routes.

## Dependencies

None. This item does not block the initial release if unresolved branches remain visible and fail safely, but it should be completed before claiming full policy coverage.

## Acceptance

- [x] Every enabled policy route resolves to an active, governed specialist.
- [x] Any intentionally unavailable route is explicitly disabled and carries a tested reason.
- [x] Policy validation fails on an unrecognized enabled slug.
- [x] Tests exercise internationalization, payments, and test-automation routing cases.
- [x] User-facing coverage documentation matches the validated roster.

## Verification

- `python scripts/update_policy_availability.py --check`
- `python -m pytest tests/test_policy_validation.py -q`
- `agency eval routing --json --no-details`
