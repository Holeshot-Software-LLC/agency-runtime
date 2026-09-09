---
title: "Apply approved Claude native tool permissions"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [claude, permissions, native]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
supersedes: []
superseded_by: null
type: worklog
commit: d0c431adade5ce44cdfb2c1beba55d4ebc8a656a
short: d0c431ad
date: 2026-09-09
pr: null
---

# Apply approved Claude native tool permissions

## Approach

The owner explicitly replied yes to adding the two exact Agency MCP Allow rules.
Added only agency_load_specialist and agency_finalize under normal user permissions;
all other settings are semantically identical, with a private backup and atomic
compare-before-replace. No bypassPermissions, server wildcard or specialist selection.
The native permission mode remains default. Evidence: AR-423-approved-tool-grant-20260909.json.

## Verification

JSON read-back and exact semantic-delta checks pass. Production source and installed
artifact remain cd86e40a/0cd4f289, unchanged from the preceding verified package.
Its production1151/3, UI224, Ruff and frozen188/188 conformance remain applicable.
The new native probe uses the exact existing large-context request, one attempt
in phase after_tool_permission with the original360second deadline. Native tool
results, exact cards, headers and accepted hash remain to be observed.

## Remaining gates

AR-423 stays open until native delivery and isolated acceptance pass. AR-404 still
owns failed staffing and missing headers, Hermes upstream adoption and Zcode gates.
AR-419 is closed only for its isolated native CLI boundary. Prior failed or denied
receipts remain unchanged. This parent turn itself failed staffing with subject and
recruiter contract rejections plus critic_wrong_neighbor_selection_discovery_coach;
no specialist or successful parent finalization is claimed.
