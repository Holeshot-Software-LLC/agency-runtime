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
branch: codex/ar423-native-context-20260909
evidence_commit: cd86e40a994bd7d6fad8699047140a8e369718a0
minimum_ledger_commit: 0cd4f2897b12f9a3de1f277303ba381dd6aa61d5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 Claude native context delivery

## Checkpoint

Scoped outcome: exact selected full cards reach Claude despite its native hook
limit, with truthful loaded evidence. Waiting_for_operator after the live-demo checkpoint; delivery PR814.
PR810 and merge ledger PR813 are merged; main b801c08f. AR-421/422 closed only
against their isolated gates. Source cd86e40a / artifact 0cd4f289 is installed; all 615 package files match.
Claude/Zcode normal refresh publishes07d88875a9e6; packaged smoke passes and
gateway RPC is healthy. After PR814 merges, this branch is historical; create a
new owned worktree for further changes. Exact merge entries live in the worklog.

## Completed evidence

Native Claude 2.1.266 hook ceiling is 10,000 UTF-16 units; the historical four-card
follow-up became a persisted pointer. The real original-source negative control
emits 15,076 units. Recipe 16 uses existing MCP retrieval of exact selected versions;
loaded rows are written only on retrieval. Shared hook no longer trims the last
card. All twelve new regression cases and 72 targeted MCP cases pass.

## Exact blocker

Fresh native full-card delivery is blocked by Claude tool permission. Four selected
cards total 11,604 UTF-16 units; the native hook is 4,741 with no pointer. All four
agency_load_specialist calls were denied; loaded evidence stays empty. Native
Stop accepts the exact truthful response. AR-423 full-card acceptance is absent. AR-424 all three isolated criteria are
satisfied; its byte-preservation scope is done, with closure in PR814.
Fast checks pass; fresh-source conformance passes 188/188.
No staffing models or provider configuration changed; failed suite outcomes remain.

## Same-task continuity

Continue this owned branch. At or below 50 percent, checkpoint the smallest safe
source/ledger pair, then continue the same task. The umbrella capsule retains
other host evidence and pending owner actions. Do not recreate historical work.

## Next bounded work package

The fixed sample retained review success, follow-up response_invalid and multi-step
staffing failure; neither staffed case exercised the large-card MCP path. The separate probe (219.959s) is retained with four native permission denials.
Wait for normal attended approval of agency_load_specialist before a new phase.
Do not change permissions or retry under the same condition. Bind full native
MCP tool results to exact session/trace and selected version/hash. Do not claim
card delivery from tool instructions alone. Build isolated acceptance afterward.

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
