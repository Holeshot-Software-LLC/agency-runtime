---
title: "AR-427: Preserve the complete inferred specialist team during hydration"
status: in_progress
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

Recipe 19 complete-team hydration is implemented. Corrected original-source
regressions fail seven cases for the omitted fifth card. Candidate focused checks
pass 66 / 1 skipped; production 1151 / 3 skipped and UI 224 pass. Frozen
conformance, installed native proof and isolated acceptance remain pending.

## Approach

Honor the already-validated durable 16-reference budget during preflight. Preserve every selected immutable reference or reject incomplete delivery; do not change staffing, trust, or native context/output ceilings. Exercise all five host paths and oversized boundaries.

## Dependencies

AR-404 owns the five-host reliability outcome. AR-423 and AR-426 retain their
native delivery and isolated acceptance gates.

## Acceptance

- [ ] Exact selected-team omission is preserved with session/trace and role evidence.
- [ ] Every inference-selected card is retained or delivery fails explicitly; host limits and load truthfulness remain enforced.
- [ ] Focused, fast and fresh installed native complete-team evidence pass.
