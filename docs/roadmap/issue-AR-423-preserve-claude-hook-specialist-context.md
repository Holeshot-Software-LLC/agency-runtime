---
title: "AR-423: Preserve Claude specialist context across native hook output limits"
status: blocked
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

Priority continuation: Claude refreshed from verified recipe20 artifact ecf8a584.
Both native MCP Allow rules remain unchanged; Claude context12 passes. One fresh
large-context native trial will capture planner initial/repair replies as well as
full card and terminal evidence before any additional isolated acceptance pass.

Fresh recipe 19 Claude session `0a59da24` / trace `28c8db15` failed two planner
contracts before delivery in 118.255s. The first lacked correctness/security review;
the second returned semantic-invalid. Full receipt is retained in
`evidence/AR-427-claude-native-after-complete-team-20260909.json`. AR-427 fixes
the prior omitted fifth card, but this failed fresh Claude turn cannot prove its
complete native delivery or resolve absent independent assurance.


The owner-authorized third isolated pass satisfied criteria 1/3 and left criterion
2 absent because independent assurance was not established. A subsequent exact
Store comparison found five inference-selected identities but only four persisted
prompt references: the independent security reviewer was omitted by a legacy
hydration cap. AR-427/#825 now owns that High defect. The four native card bodies
were delivered, but the earlier evidence does not prove the complete selected
team. AR-423 stays open; no new verdict is invented or receipt reopened.

Native large-card delivery now passes on candidate2b19cce6. Isolated acceptance
is still open: two passes yielded absent criteria1/2, partly because the pointer
row was outside the parsed table and full-file excerpts omitted later card rows.
Exact pointer evidence and a corrected contiguous, bounded packet are prepared;
local build_case verifies the pointer and native-card excerpts are included.
No third independent review in this package. Historical failed verdicts remain.


September9 candidate2b19cce6: Claude session545f5ca7-2937-412f-a9be-6b4e4c665204,
tracedf374667-2599-4798-a852-1e6f972aed25, passes the fresh large-card probe in239.508s.
Four exact selected full cards appear in same-session, exact-trace native MCP
results; all five fields match Store; accepted terminal hash
f9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b matches response.
No permission bypass or manual selection. AR-423 isolated verification follows;
AR-404 five-host fixed sample remains pending. Prior failures remain preserved.
Evidence: AR-404-claude-large-context-after-planner-context-20260909.json.


### Approved Claude permission probe outcome

Native sessionf4897a2b-8ae1-4462-a692-8cd9b53808a6, trace
be4757dc-c14f-4e39-b366-bdfa2ef0ae40, returns in101.434s, CLIexit0, no timeout.
Both bounded planner attempts are provider_response_contract_invalid (18.977s,
16.344s); staffing ends preflight_failed/inference_invalid. All five diagnostic
headers match Store, no selected cards, no MCP calls and no authoritative accepted
finalization. Native permission_denials is empty because no tool was attempted;
it is not a card-delivery canary. Both approved Allow rules remain saved.
No unchanged-condition retry. AR-423 stays open for exact native full-card and
isolated evidence; AR-404 retains staffing failures and the Hermes/Zcode gates.
Evidence: AR-404-claude-suite-after-tool-permission-20260909.json.


September9 owner-approved Claude grant: the two exact native MCP Allow rules
are now saved and read-back verified; every other setting is preserved. A fresh
one-attempt large-context probe is pending. See AR-423-approved-tool-grant-20260909.json.


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

The owner reports no startup approval prompt. Normal Claude /permissions can
add the exact per-tool Allow rules documented in troubleshooting. A narrowly
scoped user-settings write is prepared for owner approval; no grant has yet been
applied. Startup alone is not a tool-use permission request.

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
