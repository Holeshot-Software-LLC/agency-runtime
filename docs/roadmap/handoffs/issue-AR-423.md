---
title: "AR-423 Claude native context delivery checkpoint"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, claude, context]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/worklog/2026-09-09-claude-native-context-delivery.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-423
branch: codex/ar423-native-priority-20260909
evidence_commit: 5dbe612a7dd3bd7ecca1b2f60411a44b175d278f
minimum_ledger_commit: adab07907448c152e5a214e8abd5150d535f282d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 Claude native context delivery

## Checkpoint

Owner now prioritizes OpenClaw, Hermes, Codex, Claude, with Zcode deferred.
AR-428 planning repair merged in PR831 and closed with three isolated verdicts;
Hermes staffing failures remain. Codex8/8 trust and651 projection files verify.

Fresh owned branch starts at0839e158, with its exact merge ledger16ca1a0f. Claude
refreshed from recipe20 artifact ecf8a584; both exact MCP Allow rules remain saved.
One fresh large-context native trial will capture initial/repair planner replies
and full native card/terminal evidence. No stale failed receipt is reopened.

## Completed evidence

Session545f5ca7-2937-412f-a9be-6b4e4c665204,
tracedf374667-2599-4798-a852-1e6f972aed25,239.508s,4exact selected full cards
through native MCP,5Store-matching fields, accepted matching response hash
f9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b.
AR-404-claude-large-context-after-planner-context-20260909.json records exact
native tool-use/result correlation and card hashes. Planner repair and independent
critic both apply. The fixed Claude sample separately passes2/3, not all cases.

Original pointer evidence is now directly retained in
AR-423-original-native-pointer-20260909.json: native attachment81a967a9, saved
16076bytes/16067UTF16units, tracef725587c in the persisted body, same-session Store
correlation. Native limit10,000UTF16; prior denied and planner-failed probes remain.

## Exact blocker

No remaining AR-423 gate: all three isolated criteria satisfied (`7371e07f`,
`de031b6f`, `0e4e187d`) against candidate dc83cc40. Fresh native session
`a5c13def-36a1-4a3e-9484-d0f09f105209` / trace
`95f96215-d84b-4b4e-9628-c808e99b9d23` passed all4 inferred full cards,
five Store headers and authoritative hash
`1c5f87780ecf485d2f4ab4018b3a71a45c79522edd237707447667cfca638c1c`
in264.750s. No delegated specialist execution occurred or is claimed.
One planner packet captured; configuration restored byte-exact with no errors.
Broader AR-404 and Hermes AR-418 reliability remain open.

## Same-task continuity

PR832 is the owned delivery record; PR831 merge ledger is its first commit.
At or below50percent keep a clean substantive/ledger checkpoint and continue.
Both exact MCP Allow rules remain saved. No pending Codex trust or Claude tool grant.

## Next bounded work package

Merge PR832, close AR-423 and record the merge ledger. Resume AR-404's bounded
Hermes nomination-relevance diagnosis from its observed packet, preserving the
critic veto. AR-418 upstream PR106490 remains open and unadopted. Zcode stays deferred.

## Verification

Recipe20 focused164/1skip, production1151/3skip, UI224, routing, Ruff and frozen
conformance188/188 passed; canonical artifact ecf8a584 matches616 installed files.
Fresh Claude context12 passed, native4/4 complete cards and five headers/final hash
passed. Documentation1381 and strict tracker419 passed before this evidence update.
No exhaustive or Windows workflow ran; no all-host reliability claim.
