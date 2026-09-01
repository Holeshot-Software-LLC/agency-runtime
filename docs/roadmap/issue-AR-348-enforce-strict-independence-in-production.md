---
title: "AR-348: strict_independence is enforced nowhere in production"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, hiring, security, configuration]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-348
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/406
depends_on: []
blocks: []
---

# AR-348: strict_independence is enforced nowhere in production

## Problem

`enforce_strict_independence`
(`agency_runtime/core/inference_profiles.py:362-395`) is defined,
exported, and tested (`tests/test_inference_profiles.py`) but has no
production caller — a repo-wide search finds only its definition and
tests. Setting `inference.strict_independence: true` therefore silently
does nothing: a hiring security reviewer and contract creator on the
same provider are never rejected, defeating the independence control
AR-235 specified.

## Current state

Found by the AR-347 per-criterion audit of AR-235 (2026-09-01). The
config field exists (`core/config.py:348`, `config_defaults.yaml:97`),
`route_requires_independence` and `INDEPENDENCE_ROUTE_TOKENS` exist,
and same-provider detection is recorded on hiring cases — only the
enforcement call is missing.

## Approach

Call `enforce_strict_independence` where security-review providers are
resolved (the `workforce.hiring.security_review` route resolution in
`core/workforce/hiring.py`), surfacing the config error the function
already produces; add a regression test that a same-provider pairing
under `strict_independence: true` fails loudly.

## Dependencies

None; independent of the AR-235 dashboard plane.

## Acceptance

- [ ] `strict_independence: true` with a same-provider reviewer/creator
      pairing fails the hiring attempt with the documented config
      error, proven by a focused test through the production call path.
- [ ] `strict_independence: false` behavior is unchanged (warning
      recording only).
