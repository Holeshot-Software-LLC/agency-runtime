---
title: "Preserve Claude selected cards across native hook limits"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [claude, context, native, exact-delivery]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
---

# Preserve Claude selected cards across native hook limits

## Purpose

Four accepted selected cards become a native persisted-output pointer, leaving
full model-facing context unproved. The caller prohibits file reads. The shared
bridge also trims the final card's trailing whitespace.

## Approach

Recipe 16 preserves the selection and moves oversized Claude card bodies to the
existing MCP retrieval surface. Each request resolves the selected version/hash
on the exact active session/trace. Pending selection is not recorded as loading.
The hook frame reserves room for headers and the bridge guards the complete
10,000-UTF-16-unit envelope. Joining segments preserves trailing card bytes.

## Challenges encountered

The first fixture accidentally gave four workers the same primary unit; that
invalid fixture failed before delivery. Corrected bindings expose the native
limit and final-card trim. The original-source negative control asserts its
old recipe 15 and source paths, then fails at 15,076 units versus 10,000.
The first production spine finds one direct non-Claude MCP regression: consulting
a full completion snapshot on a recipe-less legacy turn raises prematurely.
Restricting versioned snapshot lookup to Claude preserves the existing behavior.
Failed logs remain local; final results are recorded below as they complete.

## Decisions and alternatives

ADR-0241 records supported versioned tool delivery and honest pending loads.
No model route, answering configuration, trust hash, critic, staffing authority
or finalization policy changes. No file-read workaround and no manual specialists.

## Verification

Twelve new regression cases pass, including immutable-version refresh, missing
version, cross-session, unselected and terminal rejection, exact inline bytes,
UTF-16 measurement and failed oversized envelopes without accepted finalization.
Targeted MCP plus new cases: 72 passed. Initial production spine: 1 failed,
1150 passed, 3 skipped; the targeted follow-up passes after the fix. Ruff check
and formatting pass (784 files). Final named spine: 1151 passed, 3 skipped in 70.30s. Expanded focused checks:
166 passed, 6 skipped in 70.05s. UI: 224 passed.
No fresh native candidate evidence or isolated acceptance yet.

## Follow-ups

Finish required checks and a fresh-source conformance run, build a verified
artifact, refresh Claude normally, and test the fixed requests with full native
MCP response evidence. Keep AR-423/424 open until isolated gates pass. AR-404
still includes Hermes, OpenClaw, Codex and Zcode; its pending operator choices
and failures remain in the umbrella capsule.
