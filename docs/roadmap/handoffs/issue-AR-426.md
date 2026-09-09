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
evidence_commit: ab924385dc8b1e7f0b2c218c2bebab55cb52b3db
minimum_ledger_commit: aee01dc6e866671db3fdc1da97e9762249028ad7
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
---

# AR-426 Hermes selected-card delivery

## Checkpoint

PR824 draft, sourceab924385/artifactaee01dc6. Recipe18 defers large selected
Hermes card sets to bounded local tool retrieval. Small inline path preserved.
All616installed files match canonical wheel; only Hermes projection refreshed.
Required fast validation passes; package demo_ready pending native proof.

## Completed evidence

Exact native messages535347/535352 prove12,991/16,585character hook spilling
removed full cards and contract. Old source regression emits15,578characters
and counts4loaded cards before delivery; its native-limit assertion fails.
Candidate native-tool regressions prove exact versions, pending/loaded split,
wrong-session/terminal/unselected/oversized rejection and result ceilings.
Baseline and fast-install JSONs live under docs/roadmap/evidence/AR-426-*.

## Exact blocker

First native phase omitted card retrieval; all3full gates remain failed.
Revised native callbacks deliver cards before model execution; fresh validation
and native full-card/header/finalization demonstration are pending. Isolated acceptance must follow that proof. AR-418
is a separate output-truncation issue: upstream PR106490 remains open, default
native checkout7cd91114 unchanged, original provider output cap unknown.

## Same-task continuity

Keep working in this owned worktree. Do not reuse historical worktrees. At50percent
ensure the smallest clean substantive/ledger checkpoint and continue this task.
No manual selection, trust changes, global spill increases or failed-receipt reopening.

## Next bounded work package

Run the three fixed Hermes requests once under360s each, retain every failure,
inspect exact native tool-call/results against selected card hashes and Store.
Then prepare isolated evidence, close only passed criteria, merge PR824 and
record exact worklog/merge ledger. AR-404 retains all five hosts and residuals.

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
