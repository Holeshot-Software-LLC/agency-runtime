---
title: "Worklog: linked roadmap, worklog, and decision system"
status: active
category: worklog
created: 2026-07-10
updated: 2026-07-10
tags: [documentation, governance, traceability]
related:
  - docs/decisions/0025-self-contained-linked-documentation.md
supersedes: []
superseded_by: null
type: worklog
commit: 4d17668695da7bdd0d32166c1bc63f56a0c91385
short: 4d17668
date: 2026-07-10
pr: null
related_issues:
  - docs/roadmap/issue-AR-08-self-contained-documentation.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
---

# Worklog: linked roadmap, worklog, and decision system

## Purpose

Establish a durable repository-local chain from planning scope to tracker
issues, implementation commits, and durable decisions. Make documentation
self-contained and replace ad hoc session context with validated registries.

## Approach

- Inventoried every maintained and historical Markdown document and derived the
  current README dates from Git history.
- Kept the project README at the repository root and placed planning, worklog,
  and decision records under `docs/`.
- Added nine standalone roadmap records with stable internal IDs, same-repo
  tracker mappings, epic labels, dependency edges, and acceptance criteria.
- Backfilled the exact 25-commit history that preceded this change and added an
  idempotent updater for future substantive commits.
- Mined the README and full commit history into 25 ADRs with five reciprocal
  supersession chains.
- Added metadata, documentation, worklog, and live tracker validators plus a
  valid in-repository roster example.

## Challenges encountered

- Only one maintained document existed, so no history-preserving moves or
  current-document retirements were justified. Two deleted historical artifacts
  were mined without being restored.
- A commit cannot contain its own SHA. The resulting ledger policy exempts only
  `docs(worklog):` commits whose changed paths are limited to `docs/worklog/**`
  and the reciprocal roadmap commit cell; the verifier enforces that boundary.
- The full Windows test run exposed eight platform-specific failures. One
  host-install test resolved the real user profile despite setting `HOME` and
  generated Codex plugin files there. The bug and related assumptions are
  tracked by AR-09; the external files were left untouched.

## Decisions and alternatives

- [ADR-0025](../decisions/0025-self-contained-linked-documentation.md) records
  the accepted self-contained traceability system.
- Deleted handoff and generated graph reports were not restored because they
  were transient or intentionally untracked, not maintained documents needing
  archival moves.
- A single global archive was rejected in favor of category-local archives
  created only when a maintained document is actually retired.

## Verification

- Metadata check passed for 40 Markdown documents before this detail file.
- Documentation schema, local links, reciprocal dependencies, and ADR
  supersession validation passed.
- Live tracker validation passed for nine roadmap items; AR-01 and AR-08 are
  closed, and AR-02 through AR-07 plus AR-09 are open.
- The in-repository roster example passed runtime candidate validation.
- The full repository suite passed 175 tests and failed eight Windows-specific
  tests now captured by AR-09.
- Staged whitespace validation passed before the substantive commit.

## Follow-ups

- [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md) must prevent tests
  from writing outside their allocated temporary root.
- Open roadmap items AR-02 through AR-07 retain their individual acceptance
  criteria and tracker mappings.
- The generated Codex user-profile plugin files from the test side effect need
  an explicit operator decision before removal or replacement.
