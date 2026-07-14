---
title: "AR-08: Make documentation self-contained"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [documentation, portability]
related:
  - docs/decisions/0025-self-contained-linked-documentation.md
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-08
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/8"
depends_on: []
blocks: [AR-07]
---

# AR-08: Make documentation self-contained

## Problem

Repository documentation must remain usable from this checkout alone. Links, examples, and operational instructions that depend on sibling repositories or machine-specific filesystem layouts make setup non-reproducible and allow external content to become an undocumented dependency.

## Current state

This item is implemented locally. The README now uses a neutral in-repository roster example, repository-owned installation URLs, and self-contained explanations. Validation rejects sibling-repository names, foreign repository URLs, placeholder absolute paths, dangling local links, and path escapes. Historical commit subjects remain unchanged and are flagged in the worklog when context is useful.

## Approach

Add a minimal governed roster example or clearly marked stub within this repository. Replace cross-repository paths and operational links with repository-local examples and neutral language while preserving the technical meaning. Preserve exact historical commit subjects; if a subject contains a scrubbed name, retain it and flag the historical exception rather than rewriting history.

## Dependencies

None. This documentation cleanup is part of the release-readiness gate in `AR-07`.

## Acceptance

- [x] Every documented setup and roster workflow can be followed using only this repository and named runtime services.
- [x] No maintained document links to or depends on another repository's files.
- [x] No machine-specific sibling path appears in maintained documentation.
- [x] Required examples are stored in-repository or represented by an explicit, self-contained stub.
- [x] Historical commit subjects remain faithful and any unavoidable name reference is flagged as historical.
- [x] Documentation link and forbidden-reference validation passes.
