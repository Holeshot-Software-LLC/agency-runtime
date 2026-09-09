---
title: "AR-423: Preserve Claude specialist context across native hook output limits"
status: open
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [claude, context, native, reliability]
related:
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
  - docs/worklog/2026-09-09-claude-native-context-delivery.md
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

Read-only inspection of the installed2.1.266 binary identifies a10,000JavaScript
string-length default for the native hook persistence helper. The observed15.7KB
is payload size, not the limit. Four selected full cards alone exceed10,000characters;
trimming the frame cannot preserve them all. See
[evidence/AR-423-claude-native-hook-limit-20260909.json](evidence/AR-423-claude-native-hook-limit-20260909.json).
No supported threshold override has been established.

The owned candidate uses recipe 16 to keep a bounded hook frame and retrieve
large card sets through the existing MCP tool. Retrieval is restricted to the
selected immutable version and exact active turn; pending cards do not appear
loaded. The final emitted envelope is checked in UTF-16 units. Source cd86e40a and artifact 0cd4f289 are installed; all 615 package files match.
Claude/Zcode normal refresh and packaged smoke pass. Draft PR814 owns the change.
The fixed sample retains an accepted review, header-invalid follow-up and staffing-failed
multi-step. Its staffed cases used inline single cards. A separately frozen four-card native probe emits 4,741 UTF-16 units for 11,604
units of selected cards; no persisted pointer. All four MCP loads are denied by
native tool permissions. Loaded evidence stays empty and the five headers remain
truthful. The normal Stop hook accepts the exact final response, but card delivery
is unproved. State: waiting_for_operator for normal agency_load_specialist permission.
No permission override or trust bypass. Isolated acceptance remains pending.
Original-source integration emits 15,076 units and fails the real-hook regression.

## Approach

Identify the native inline limit and supported delivery surface. Preserve exact
selected versions, inference authority, independent critic, caller scope and
truthful loaded evidence. Verify full native model-facing cards before acceptance.

## Dependencies

AR-404 retains the fixed native sample; AR-421 owns completed-task classification.
AR-422 owns executable installation only.

## Acceptance

Repository-required isolated verdicts govern closure after these criteria are judged.

- [ ] Reproduce the native pointer substitution with exact bounded evidence.
- [ ] Deliver the selected full cards through a supported native surface without
      bypassing caller scope, trust, inference or independent assurance.
- [ ] Verify regression and fresh native evidence.
