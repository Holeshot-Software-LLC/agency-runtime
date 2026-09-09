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
evidence_commit: 3a921c61ab8f909f4630ca9fc60a4e9fbb0d04a2
minimum_ledger_commit: 855c20785989dcb0fb6d74a108f4a4ad9e576b85
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 Claude native context delivery

## Checkpoint

Scoped outcome: exact selected full cards reach Claude despite its native hook
limit, with truthful loaded evidence. Implementing on the owned branch above.
PR810 and merge ledger PR813 are merged; main b801c08f. AR-421/422 closed only
against their isolated gates. Current source candidate is not installed yet.

## Completed evidence

Native Claude 2.1.266 hook ceiling is 10,000 UTF-16 units; the historical four-card
follow-up became a persisted pointer. The real original-source negative control
emits 15,076 units. Recipe 16 uses existing MCP retrieval of exact selected versions;
loaded rows are written only on retrieval. Shared hook no longer trims the last
card. All twelve new regression cases and 72 targeted MCP cases pass.

## Exact blocker

Fresh native full-card delivery and isolated AR-423/424 acceptance are absent.
Required full fast checks and fresh-source conformance are still being completed.
No staffing models or provider configuration changed; failed suite outcomes remain.

## Same-task continuity

Continue this owned branch. At or below 50 percent, checkpoint the smallest safe
source/ledger pair, then continue the same task. The umbrella capsule retains
other host evidence and pending owner actions. Do not recreate historical work.

## Next bounded work package

Finish checks, open PR, verify wheel against clean source, refresh Claude normally
and run the fixed review/follow-up/native multi-step sample once. Bind full native
MCP tool results to exact session/trace and selected version/hash. Do not claim
card delivery from tool instructions alone. Build isolated acceptance afterward.

## Verification

Twelve regressions pass; 72 targeted MCP cases pass. Initial spine found one
non-Claude recipe-less MCP regression (1150 pass, 3 skip), repaired and targeted
checks pass. Ruff check/format pass. Final spine: 1151 passed, 3 skipped; expanded focused checks: 166 passed,
6 skipped. UI: 224 passed.
Old conformance 188/188 covers cf4ed77f only; a new frozen-source run is required.

## Constraints

Inference alone selects staff; preserve critic, validators, trust, caller scope
and finalization. No file-read workaround, model change, manual specialist,
unbounded retry or manual failed-receipt acceptance. Keep all five hosts in scope.
Owned worktree, PR, merge and exact worklog records are mandatory.
