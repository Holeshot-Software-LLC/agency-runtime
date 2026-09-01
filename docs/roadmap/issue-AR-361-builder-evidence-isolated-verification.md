---
title: "AR-361: Split acceptance into builder evidence and isolated single-check verification"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [acceptance, evidence, verification, process]
related:
  - docs/roadmap/AR-256-done-acceptance-reconciliation.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-361
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/434
depends_on: []
blocks: []
---

# AR-361: Split acceptance into builder evidence and isolated single-check verification

## Problem

Acceptance boxes are graded by whoever did the work. The gates only
check that boxes are checked, so "done" can drift from reality until a
manual reconciliation: the 2026-08-30 pass found nine done-docs whose
acceptance did not hold and forced eight tracker reopens (AR-256
records the disposition). Self-grading is the root gap.

## Current state

`verify_docs` refuses done flips with unchecked boxes — a syntactic
guard only. Nothing separates who cites evidence from who judges it,
and no isolated context re-derives a verdict from the evidence.

## Approach

Adopt the two-phase pattern (lifted from LobeHub's acceptance-evidence
tool and verify-agent, owner-approved 2026-09-01), on our existing
isolated-worker machinery:

1. **Builder evidence phase**: after work completes, the builder cites
   concrete evidence per acceptance criterion — command output, file
   paths, receipt ids — and is explicitly forbidden from judging or
   inventing; missing evidence is stated plainly.
2. **Isolated verification phase**: a verifier with a deliberately
   minimal toolset (verdict writeback plus injected read-only
   investigation tools) judges exactly one criterion per run and must
   submit its verdict through the tool to be recorded.

Start with roadmap-doc acceptance (the measured failure), leaving room
to extend to workforce completion criteria later.

## Dependencies

- None; uses existing isolated_only worker plumbing.

## Acceptance

- [ ] A done flip requires per-criterion builder evidence records, not
      just checked boxes.
- [ ] Each criterion's verdict comes from an isolated single-check
      verifier run, recorded with the evidence it judged.
- [ ] A criterion with absent or contradicted evidence fails verification
      and blocks the done flip, covered by regression tests.
