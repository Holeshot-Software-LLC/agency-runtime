---
title: "AR-213: Reject stale preflight tokens before plan validation"
status: done
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [bug, preflight, concurrency, fencing]
related:
  - agency_runtime/core/store/preflight.py
  - tests/test_preflight_bounds.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-213
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/209
depends_on: []
blocks: []
---

# AR-213: Reject stale preflight tokens before plan validation

## Problem

After a newer owner recovers an expired preflight attempt, a stale caller to
`mark_preflight_ready` can reach Codex native-plan-scope validation before the
attempt token is rejected. A stale request with an otherwise incomplete recipe
therefore raises `ValueError` instead of returning `False` without mutation.

## Current state

The unrelated failure surfaced during the bounded AR-212 compatibility run in
`test_expired_owner_is_recovered_and_stale_token_cannot_commit_or_fail`. AR-212
does not change this store boundary, and its required focused tests remain
green, so this defect is recorded separately rather than expanding that
delivery package.

The same node failed twice on the `824bb8b` base during AR-220's optional
broader diagnostic slice, after 164 other routing, hiring, selection, and
preflight checks passed with one skip. It remains a known independent fencing
defect and is not part of the AR-220 gap-hiring package or named fast spine.

## Approach

Resolve and fence the exact current attempt owner before recipe-specific native
plan validation or any write. Preserve strict validation for the current owner
and prove that stale tokens cannot commit, fail, or trigger recipe-validation
errors after recovery.

## Dependencies

None. Coordinate with the existing preflight atomicity and native Codex plan
scope contracts.

## Acceptance

- [x] A stale ready token returns `False` before native-plan-scope validation.
- [x] The current owner still receives strict complete-plan validation.
- [x] Stale commit and stale failure paths make no durable mutation.
- [x] Focused preflight fencing and native plan scope tests pass.
