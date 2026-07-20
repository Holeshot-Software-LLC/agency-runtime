---
title: "AR-102: Refresh legacy bundled roster contracts on upgrade"
status: done
category: roadmap
created: 2026-07-19
updated: 2026-07-20
tags: [roster-governance, upgrade, routing, compatibility, installation]
related:
  - docs/roadmap/issue-AR-02-specialist-coverage-gaps.md
  - docs/roadmap/issue-AR-26-bundle-default-coordinators.md
  - docs/roadmap/issue-AR-91-enforce-governed-roster-activation.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-102
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/103"
depends_on: []
blocks: []
---

# AR-102: Refresh legacy bundled roster contracts on upgrade

## Problem

Older installations can retain package-owned starter rows created before
governed routing contracts were added. Missing-only starter seeding leaves
those legacy rows active after an upgrade, so compatibility correctly rejects
important specialists such as `code-reviewer`, `technical-writer`, and
`senior-developer` as `invalid_routing_contract`. Per-unit routing can then
recommend a weaker but contract-valid specialist from the same broad token
neighborhood.

## Current state

A real installed Windows dashboard route reproduced the defect. The seed path
now refreshes only rows matching one of the seven immutable historical prompt-
hash and active-projection-hash identities, and per-unit routing filters
mutation candidates by reviewed authority before inference. Focused regressions
select `code-reviewer`,
`minimal-change-engineer`, and `technical-writer` while preserving current,
synced, operator-owned, and merely bundled-looking rows. Upgrade receipts report
additions and migrations separately. The rebuilt wheel repaired the real legacy
Windows database in place; Route Lab then produced those exact three specialists
with no invalid-contract rejection, and a second install was a zero-change
no-op. The warning-strict suite and exact branch coverage pass; clean-artifact
and hosted proof remain.

## Approach

During idempotent starter seeding, replace only rows whose complete persisted
identity matches the immutable allowlist for the released seven-agent starter
roster: slug, version, source, empty legacy provenance, prompt URI, prompt
content hash, active projection hash, and internally consistent stored hashes.
Refresh those rows from the current audited package manifest, including their
routing contracts and provenance. Preserve every synced, approved-candidate,
custom, or otherwise operator-owned active row, even when its slug and storage
shape resemble a bundled specialist. Keep current bundled rows as no-ops.

## Dependencies

ADR-0013 requires bundled seeding to preserve activated synced specialists.
AR-91 defines the governed activation boundary. The migration must satisfy
both by narrowing replacement authority to exact legacy package ownership
evidence.

## Acceptance

- [x] Exact legacy package-owned starter rows refresh to current audited bundled contracts.
- [x] Current bundled rows remain idempotent no-ops.
- [x] Synced, approved-candidate, and operator-owned rows are never overwritten.
- [x] Upgraded routing selects relevant security, implementation, and documentation specialists for the reproduced task.
- [x] Fresh install, upgrade, full-suite, and hosted Windows/Linux gates pass.
