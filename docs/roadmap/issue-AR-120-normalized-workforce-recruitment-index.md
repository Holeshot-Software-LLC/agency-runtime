---
title: "AR-120: Normalize and audit the complete workforce recruitment index"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [roster, taxonomy, audit, ingestion]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-120
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/133
depends_on: []
blocks: [AR-121, AR-122, AR-125]
---

# AR-120: Normalize and audit the complete workforce recruitment index

## Problem

The roster's rich prompt metadata is not a normalized recruitment ontology, so
near-neighbor roles, stacks, lifecycle phases, tools, and composition rules are
too easy to confuse.

## Current state

All approved prompt bodies have audit provenance, but categories and tool terms
are highly fragmented and `conflicts_with` overloads several distinct meanings.

## Approach

Build and version a compact contract for every worker, audit each projection
against its source prompt, normalize vocabularies and typed relationships, and
maintain independent confusion groups and ingestion evaluations.

## Dependencies

The existing audited roster and quarantine pipeline remain authoritative for
prompt provenance and activation approval.

## Acceptance

- [ ] Every governed worker has a complete normalized recruitment contract.
- [ ] Typed relationships replace overloaded conflict semantics.
- [ ] Every projection is independently checked against its prompt body.
- [ ] Nightly ingestion updates contracts, confusion groups, and evaluations safely.
