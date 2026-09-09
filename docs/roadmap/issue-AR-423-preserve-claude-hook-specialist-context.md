---
title: "AR-423: Preserve Claude specialist context across native hook output limits"
status: open
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [claude, context, native, reliability]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0016-central-finalization-and-session-correlation.md
  - docs/worklog/2026-09-09-completed-task-context.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-423
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
depends_on: []
blocks: []
---

# AR-423: Preserve Claude specialist context across native hook output limits

## Problem

Claude replaces a large Agency hook context with a persisted-output pointer.
Accepted staffing and truthful output headers therefore do not prove full
model-facing specialist delivery. A caller who prohibits file access cannot
safely be worked around by reading that file automatically.

## Current state

Claude2.1.266 session3997acd8-f882-47ac-b4d2-e7a591193b10, follow-up trace
f725587c-7478-4fdb-8f8b-ba1c58e57b73: classifier6 preserves completed-task context,
fresh inference selects four specialists and the response finalizes. Native
hook_additional_context instead contains an Output-too-large15.7KB file pointer.
The ordinary one-specialist review has exact full-card evidence. See the retained
AR-404-claude-suite-after-repair-20260909.json evidence in this repository.

## Approach

Identify the native inline limit and supported delivery surface. Preserve exact
selected versions, inference authority, independent critic, caller scope and
truthful loaded evidence. Verify full native model-facing cards before acceptance.

## Dependencies

AR-404 retains the fixed native sample; AR-421 owns completed-task classification.
AR-422 owns executable installation only.

## Acceptance

- [ ] Reproduce the native pointer substitution with exact bounded evidence.
- [ ] Deliver the selected full cards through a supported native surface without
      bypassing caller scope, trust, inference or independent assurance.
- [ ] Verify regression and fresh native evidence through isolated acceptance.
