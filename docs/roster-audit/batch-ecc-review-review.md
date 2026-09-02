---
title: "Roster audit batch: ECC review cards"
status: active
category: governance
created: 2026-09-02
updated: 2026-09-02
tags: [roster, audit, review, ecc]
related:
  - docs/roster-audit/batch-ecc-review.json
  - docs/roster-audit/audit-manifest.json
  - docs/roadmap/issue-AR-364-audit-external-review-cards.md
supersedes: []
superseded_by: null
---

# Roster audit batch: ECC review cards

## Result

Two of two source definitions approved as governed contracts; zero
quarantined, zero retired. Both are `direct_safe` (no required tools) with
`review` authority, so neither can ever be staffed on implementation-authority
work (`_AUTHORITY_COMPATIBILITY` admits only `review` contracts to a `review`
unit and only `modify` contracts to a `modify` unit).

## Scope

Source: the ECC catalog pinned at revision `ca185ef5f7667078a1e70a763bd3a9c71c48acf0`
(MIT), audited as an explicit-inventory source: only the two audited paths
belong to the package; the repository is tooling and documentation otherwise.
Both cards were approved by the owner on 2026-09-01 (AR-364) for two review
dimensions with measured misses in this repository's own history: silent
failures (the fail-open family) and type design (representable illegal
states).

## Safety and quality findings

| Finding | Disposition |
|---|---|
| A "Prompt Defense Baseline" block precedes both cards | Stripped; it is host policy, never specialist expertise, and the governed prompt renders only audited fields |
| Model pins (`sonnet`) and tool pins (`Read`, `Grep`, `Glob`, `Bash`) in the front matter | Dropped; the host proves tool availability, the runtime never assumes it |
| Output-format sections read as instructions to the host | Projected into `expected_output_contract` and `evidence_requirements` only |
| No memory, persistence, or external-access claims | None found; nothing to bound |

## Portability projection

Both cards run on every execution host and both platforms; `direct_safe`
because they read and report only.

## Conflict and composition notes

No conflicts or requirements. Distinct independence groups
(`engineering-silent-failure-review`, `engineering-type-design-review`) so
either can serve as the independent reviewer after an implementing unit.
