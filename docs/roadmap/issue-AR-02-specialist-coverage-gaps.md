---
title: "AR-02: Close specialist coverage gaps"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [roster, policy]
related:
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-02
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/2"
depends_on: []
blocks: []
---

# AR-02: Close specialist coverage gaps

## Problem

The bundled companion policy contains conditional routes to specialist slugs that are not present in the active starter roster. Those branches cannot resolve when a user relies only on repository-provided data.

## Current state

The policy references `internationalization-engineer`, `payments-billing-engineer`, and `test-automation-engineer`, while the current starter roster does not activate those specialists. The README reports these as coverage gaps, and the same slugs appear in multiple policy actions.

## Approach

Resolve each gap deliberately: add an in-repository, governed specialist definition when the role is genuinely required, or map the condition to an existing specialist with equivalent responsibility. Keep policy validation strict so a new unresolved slug cannot be introduced silently.

## Dependencies

None. This item does not block the initial release if unresolved branches remain visible and fail safely, but it should be completed before claiming full policy coverage.

## Acceptance

- [ ] Every enabled policy route resolves to an active, governed specialist.
- [ ] Any intentionally unavailable route is explicitly disabled and carries a tested reason.
- [ ] Policy validation fails on an unrecognized enabled slug.
- [ ] Tests exercise internationalization, payments, and test-automation routing cases.
- [ ] User-facing coverage documentation matches the validated roster.
