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
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/818
related_issues:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
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

The 12 focused Claude context-delivery tests pass in8.80s. The first docs check
found missing related_issues front matter in this new worklog; added before final
validation. No production source was changed.


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

Grant package complete; the native full-card outcome remains blocked by inference.
No new owner permission is pending for these two tools. Production and installed
sources remain unchanged. Docs/metadata/policy/tracker and focused12 checks pass.

## Merged delivery

PR818 merged2026-09-09T14:50:27Z as68383aac6b67c97b433a753e5b16b65b625a7dd0.
Exact subject: `Merge pull request #818 from Holeshot-Software-LLC/codex/ar423-claude-tool-grant-20260909`.
The grant is complete. AR-423/AR-404 remain open after the native staffing failure.
No owner approval remains pending for these two rules.
