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
branch: codex/ar423-claude-tool-grant-20260909
evidence_commit: cd86e40a994bd7d6fad8699047140a8e369718a0
minimum_ledger_commit: 0cd4f2897b12f9a3de1f277303ba381dd6aa61d5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 Claude native context delivery

## Checkpoint

PR818 grant applied; fresh probe101.434s fails both bounded planner attempts
(provider_response_contract_invalid). No team/MCP calls or accepted finalization.
Permission denials empty does not prove native card delivery. AR-423 stays open.


Scoped outcome: exact selected full cards reach Claude despite its native hook
limit, with truthful loaded evidence. Owner approved both exact Allow rules; they are applied and read-back verified.
PR814 and merge ledger PR815 are merged; base main f013e63a. AR-421/422/424
closed only against their isolated gates. Current owned branch is shared-staffing
PR816. Source cd86e40a / artifact0cd4f289 remains installed;615files match.
Claude/Zcode projection07d88875a9e6 is unchanged. The older native-context branch
is historical. The new worklog documents normal /permissions Allow rules;
startup alone does not prompt. The explicit yes authorizes this grant.

## Completed evidence

Native Claude 2.1.266 hook ceiling is 10,000 UTF-16 units; the historical four-card
follow-up became a persisted pointer. The real original-source negative control
emits 15,076 units. Recipe 16 uses existing MCP retrieval of exact selected versions;
loaded rows are written only on retrieval. Shared hook no longer trims the last
card. All twelve new regression cases and 72 targeted MCP cases pass.

## Exact blocker

Native full-card gate now has a fresh successful candidate2b19cce6 probe:
session545f5ca7-2937-412f-a9be-6b4e4c665204, tracedf374667-2599-4798-a852-1e6f972aed25,
239.508s,4exact selected cards through normal approved MCP tools,5matching fields,
accepted responsef9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b.
Source delivery regressions12pass; isolated acceptance pending. Earlier denied
and planner-failed probes stay preserved; no manual staffing or acceptance.

## Same-task continuity

After PR818 merges, this grant branch is historical; create a new owned worktree. At or below
50 percent, checkpoint the smallest safe
source/ledger pair, then continue the same task. The umbrella capsule retains
other host evidence and pending owner actions. Do not recreate historical work.

## Next bounded work package

Complete isolated AR-423 acceptance from the fresh exact native evidence in
AR-404-claude-large-context-after-planner-context-20260909.json and required
checks. AR-404 runs the fixed three-case sample on all five hosts separately.
Current owned branchcodex/ar404-planner-contract-20260909, PR821; prior branch
is historical and merged. Both Claude tool grants are applied, no operator wait.

## Verification

Twelve regressions pass; 72 targeted MCP cases pass. Initial spine found one
non-Claude recipe-less MCP regression (1150 pass, 3 skip), repaired and targeted
checks pass. Ruff check/format pass. Final spine: 1151 passed, 3 skipped; expanded focused checks: 166 passed,
6 skipped. UI: 224 passed.
Fresh-source conformance passes 188/188, no survivors/invalid mutations, source unchanged.

## Constraints

Inference alone selects staff; preserve critic, validators, trust, caller scope
and finalization. No file-read workaround, model change, manual specialist,
unbounded retry or manual failed-receipt acceptance. Keep all five hosts in scope.
Owned worktree, PR, merge and exact worklog records are mandatory.
