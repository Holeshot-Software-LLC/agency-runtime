---
title: "AR-426 Hermes context delivery checkpoint"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, hermes, context]
related:
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
  - docs/decisions/0244-deliver-large-hermes-card-sets-through-native-tools.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-426
branch: codex/ar404-terminal-reliability-20260909
evidence_commit: faf5645a6e7b9c86b15d6caad52b7ddbea6f032a
minimum_ledger_commit: 22f24eddeb5fc43a017c7d774f2fd14d1b727988
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
---

# AR-426 Hermes selected-card delivery

## Checkpoint

PR 824 remains draft. Callback source faf5645a / artifact 22f24edd is installed;
616 exact file matches. Focused 131, production 1151 / 3 skipped, UI 224 and
conformance 188/188 pass. Only the Hermes native projection was refreshed.

Both three-case native phases failed the full acceptance gate. The tool-only
phase omitted card retrieval; the callback phase failed staffing before delivery.
The second phase records review coverage/confidence rejection, follow-up critic
veto, and a 60-second planner timeout. No failed receipt is reopened.

## Completed evidence

Exact native messages535347/535352 prove12,991/16,585character hook spilling
removed full cards and contract. Old source regression emits15,578characters
and counts4loaded cards before delivery; its native-limit assertion fails.
Candidate native-tool regressions prove exact versions, pending/loaded split,
wrong-session/terminal/unselected/oversized rejection and result ceilings.
Baseline and fast-install JSONs live under docs/roadmap/evidence/AR-426-*.

## Exact blocker

No callback candidate native turn has yet passed staffing, so native delivery,
five-header and authoritative finalization proof remain absent. The single post-timeout attempt took 91.605 seconds and failed the critic,
with no finalization events. No further attempt is scheduled. AR-426 is blocked
by shared staffing; an isolated record separates source evidence from absent
native acceptance.

AR-418 remains separate: upstream PR 106490 is open, default native checkout
7cd91114 is unchanged, and the original provider output cap is unknown.

## Same-task continuity

Keep working in this owned worktree. Do not reuse historical worktrees. At50percent
ensure the smallest clean substantive/ledger checkpoint and continue this task.
No manual selection, trust changes, global spill increases or failed-receipt reopening.

## Next bounded work package

Complete the isolated evidence record and read-only tracker/document checks,
push the clean owned branch and keep PR 824 draft. The next implementation
package must diagnose shared staffing with sufficient bounded evidence before
choosing a repair; retained content-free veto receipts do not prove a critic bug.
Do not schedule another unchanged native attempt or weaken staffing for a demo.

## Verification

Context/terminal75pass, wider121pass/6skip, production1151pass/3skip, UI224pass.
Routing/Ruff/format/metadata/docs/strict tracker417pass; conformance188/188,
0invalid/0survived. Canonical build/Twine/artifact/installed smoke pass,616file
match. Shared-clone build output-limit failure retained; private exact clone
succeeds unchanged. No exhaustive or Windows workflow.

## Constraints

Inference selects staff; preserve independent critic, validators and trust.
Codex current parent6db15efbecbe/8trusted; other native projections unchanged.
AR-423 corrected third isolated packet awaits explicit authorization; no reply
is not approval. Zcode first prefix rejection is valid, staffing critic veto
correctness remains unknown without failed selection content.
