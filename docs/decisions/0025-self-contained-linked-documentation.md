---
title: Keep a self-contained planning-to-evidence documentation chain
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-13
tags: [documentation, governance, traceability]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-08-self-contained-documentation.md
  - docs/roadmap/issue-AR-20-full-history-ledger-ci.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0025
type: decision
deciders: []
---

# ADR-0025: Keep a self-contained planning-to-evidence documentation chain

## Context

The repository had a comprehensive landing page and a deleted session handoff, but no durable system connecting planned work, tracker state, implementation history, and architectural decisions. Some documentation also depended on sibling-repository paths or names for context.

## Decision

Make docs the root for maintained planning, worklog, and decision records. Keep roadmap items under docs/roadmap, commit evidence under docs/worklog, and this single-number decision registry under docs/decisions.

Every maintained Markdown document carries a small shared front matter core. Roadmap records use stable internal identifiers that remain distinct from tracker numbers. Worklog indexes preserve faithful commit subjects. Superseded records link in both directions.

Documentation must stand on repository-local context. Bring required examples into this repository or write a neutral stub. Do not make understanding a document depend on a sibling repository, external filesystem path, or renamed project. Preserve faithful historical subjects and flag their provenance rather than rewriting history.

## Consequences

- A reader can move from intent to tracker item, commit evidence, and durable rationale.
- Metadata and indexes require validation as part of ordinary changes.
- External tracker URLs may identify outward work, but the local record remains independently understandable.
- Historical documents can be retired without deleting the reasoning they contributed.

## Alternatives

- Keep planning only in an external tracker. Rejected because repository history would lose local scope and acceptance context.
- Keep one large session handoff. Rejected because it becomes stale and mixes plans, implementation notes, and durable decisions.
- Maintain cross-repository documentation links. Rejected because they make this repository's operating contract depend on separately changing content.

## Provenance

This decision was accepted during the 2026-07-10 documentation-system design review. The full sweep used the current README, the intentionally removed historical handoff from commit 8f6d320, and all 25 repository commits while leaving deleted generated reports deleted.
