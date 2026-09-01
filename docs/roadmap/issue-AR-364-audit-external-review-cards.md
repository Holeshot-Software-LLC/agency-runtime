---
title: "AR-364: Audit two external review cards into the governed roster"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [roster, audit, specialists, review]
related:
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-364
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/437
depends_on: []
blocks: []
---

# AR-364: Audit two external review cards into the governed roster

## Problem

The roster has no specialist for two review dimensions with measured
misses in this repo's own history: silent failures (the AR-344/345/346
fail-open family was exactly swallowed-error/dangerous-fallback
defects) and type design (AR-343/AR-351 were representable-illegal-
state defects). Owner reviewed external catalogs 2026-09-01 and
approved auditing in two cards from affaan-m/ECC.

## Current state

Candidate source cards identified: `agents/silent-failure-hunter.md`
and `agents/type-design-analyzer.md` in affaan-m/ECC. Both are small,
read-only review personas with concrete finding rubrics; neither
overlaps an existing card in the index.

## Approach

Run both through the standard contractor audit pipeline exactly like
the existing governed imports: pin source URL + SHA-256 provenance, strip
host-specific boilerplate (their "Prompt Defense Baseline" blocks),
derive authority/context-mode/task-types/capabilities/anti-use
sections, record known audit constraints, and land them as governed
contracts. No shortcut path: if a card fails audit, record why and do
not add it.

## Dependencies

- None; uses the existing audit pipeline.

## Acceptance

- [ ] Both cards exist as governed contracts with pinned provenance
      (source URL + SHA-256 + audit revision) or a recorded audit
      rejection.
- [ ] Routing evidence shows each card is reachable by inference for a
      matching request shape (a silent-failure review ask and a type
      design review ask).
- [ ] Neither card can be selected for implementation-authority work
      (review authority only).
