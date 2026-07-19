---
title: "AR-91: Enforce governed roster activation at every public store boundary"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-19
tags: [roster, activation, governance, security]
related:
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-91
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/92"
depends_on: [AR-28, AR-83, AR-86]
blocks: [AR-95]
---

# AR-91: Enforce governed roster activation at every public store boundary

## Problem

The public Store activation and upsert APIs can write an arbitrary normalized
specialist directly into `agent_active` without a candidate, deterministic and
semantic audit, approved snapshot, or activation receipt. A synthetic unknown
agent was proven active with zero candidate, snapshot, and audit rows.

## Current state

Every public activation and upsert boundary now requires either an exact
verified bundled contract or validated approved-candidate authority before
opening the store. The installation-only seed boundary is explicit,
idempotent, and non-replacing for operator-owned active revisions.

## Approach

Fail closed at public activation and upsert boundaries unless the exact
definition is a verified packaged bundled contract or carries validated
approved-candidate activation authority. Isolate installation-only bundled
seeding behind an explicit internal API. Preserve immutable version checks and
generation accounting.

## Dependencies

AR-28 owns reversible availability, AR-83 owns manifest quarantine, and AR-86
owns the complete upstream lifecycle.

## Acceptance

- [x] Unknown synthetic definitions cannot become active through public Store APIs.
- [x] Exact verified bundled definitions can seed without overwriting operator-owned active versions.
- [x] Approved candidate activation remains the only path for imported or changed definitions.
- [x] Direct upsert aliases cannot bypass the same checks.
- [x] Refusal leaves no active, version, or category residue.
- [ ] Full coverage, documentation, packaging, Windows, and Linux gates pass.
