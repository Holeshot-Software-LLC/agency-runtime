---
title: "AR-415: Respect negated change requests in plan completeness"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [planning, scope, reliability]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/2026-09-08-negated-request-scope.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-415
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/778
depends_on: []
blocks: []
---

# AR-415: Respect negated change requests in plan completeness

## Problem

The native AR-414 review check explicitly said it was not a request to change
the repository. The lexical completeness checker nevertheless treated `change`
as a positive mutation instruction, demanded implementation and assurance units,
then demanded release verification because the request mentioned installed hooks.

## Current state

Phase waiting_for_operator. Two regression cases fail before the repair. Bounded
nominal exclusions now leave a read-only plan intact. Separate positive clauses
retain the original completeness requirements. Implementation c1ef8566 is merged
through PR779/d0bb4127 and installed. All614package files match the independently
verified wheel. Installed exclusions pass; all six positive clause boundaries
still require implementation. Focused185, production1151/3skip and UI224pass.
The refreshed Codex plugin has8modified hooks and needs fresh approval before
native verification; the earlier artifact's native diagnostic is not reused as
this repair's native proof. Acceptance remains unchecked and the issue stays open.

## Approach

Extend exclusion recognition only for `not a request to` and `not asking [you]
to`. Stop at punctuation, newlines or a contrastive `but`. Preserve the original
plan, schemas, dependency checks, staffing verifier and inference authority.
This is a parsing repair, not a general natural-language intent classifier.

## Dependencies

AR-414 provides the working installed diagnostic header used to identify this
failure. No provider reconfiguration or new credential is needed.

## Acceptance

- [ ] A read-only plan is not rejected for mutation requirements solely because
      the request explicitly says `not a request to change` or `not asking you
      to change`; regression evidence includes the prior failure.
- [ ] Separate positive mutation clauses still require implementation and
      assurance, and other planning and staffing validators remain intact.
- [ ] The installed repair and a normal native invocation show the corrected
      scope behavior; exact evidence, limitations and repository records agree.
