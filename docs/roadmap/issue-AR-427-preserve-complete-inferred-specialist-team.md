---
title: "AR-427: Preserve the complete inferred specialist team during hydration"
status: done
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, workforce, evidence]
related:
  - docs/decisions/0245-preserve-complete-inferred-teams-during-delivery.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-427
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/825
depends_on: []
blocks: []
---

# AR-427: Preserve the complete inferred specialist team during hydration

## Problem

Inference selected five workers in Claude trace df374667, including an independent security reviewer. Direct hydration silently capped the set at four. A later authoritative finalization accepted the partial delivery. This is a High reliability finding: an assurance worker can be omitted after the workforce verifier and critic approve the team.

## Current state

All three isolated criteria are satisfied in `acceptance/issue-AR-427.md`.
AR-426 used the owner-authorized third pass; AR-427 used its first pass.
PR 824 merged at `e81f8e00`; tracker closure is complete. Earlier failed native receipts remain failed.


Recipe 19 source `176adc19` implements complete-team hydration. Corrected
original-source regressions fail seven cases for the omitted fifth card; candidate
focused 66 / 1 skipped, production 1151 / 3 skipped, UI 224 and frozen conformance
188/188 pass. Canonical artifact source `20c49e0d` passes independent distribution,
installed smoke and 616-file identity checks.

Fresh Hermes session `20260909_143551_e08888` passed in 114.863s with five
inferred identities equal to five persisted references, all five full native cards,
five Store-matching headers and authoritative accepted response hash
`6546ecb6525a7f1237f47e519b7971574e9d7424862bf50e23ee364f9a980968`.
The first isolated acceptance pass satisfied all criteria. Fresh Claude trace `28c8db15`
failed two planner contracts before delivery; no Claude success is inferred.

OpenClaw refresh completed and gateway RPC is healthy. Codex's eight hooks are
now trusted; a fresh native process uses published projection `37c1bf7d5eb0`,
while the existing parent remains on `6db15efbecbe`. Its fresh native probe passed in 103.434s with all five inferred cards, matching
headers and authoritative response hash `72f3a83528f0165e820684d23f3cd1b3394d2ae1b30c9805a4da06e81acc85e0`. No all-host reliability claim is made.

## Approach

Honor the already-validated durable 16-reference budget during preflight. Preserve every selected immutable reference or reject incomplete delivery; do not change staffing, trust, or native context/output ceilings. Exercise all five host paths and oversized boundaries.

## Dependencies

AR-404 owns the five-host reliability outcome. AR-423 and AR-426 retain their
native delivery and isolated acceptance gates.

## Acceptance

- [x] Exact selected-team omission is preserved with session/trace and role evidence.
- [x] Every inference-selected card is retained or delivery fails explicitly; host limits and load truthfulness remain enforced.
- [x] Focused, fast and fresh installed native complete-team evidence pass.
