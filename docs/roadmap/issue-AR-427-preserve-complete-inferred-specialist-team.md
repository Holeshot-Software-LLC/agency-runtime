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

Fresh recipe 19 Hermes turn `20260909_143551_e08888` completed in 114.863s
with all five inference-selected cards present in native message 535391, five
matching Store headers and authoritative response hash
`6546ecb6525a7f1237f47e519b7971574e9d7424862bf50e23ee364f9a980968`.
The exact context, full cards, terminal and installed validation are retained under
AR-427 evidence. Isolated acceptance is now pending. Earlier failures below are
historical and remain failed. Fresh Claude trace `28c8db15` failed planner validation
before card delivery; it does not establish a Claude native gate.


Recipe 19 complete-team hydration is implemented. Corrected original-source
regressions fail seven cases for the omitted fifth card. Candidate focused checks
pass 66 / 1 skipped; production 1151 / 3 skipped and UI 224 pass. Frozen
conformance passes 188/188. Canonical recipe 19 artifact at `20c49e0d` passes
independent distribution and installed smoke checks; all 616 installed files match.
OpenClaw refresh is complete and gateway RPC healthy. Codex native trust review
and a fresh process remain pending. Fresh native complete-team proof and isolated
acceptance remain pending. See `evidence/AR-427-installed-fast-validation-20260909.json`.

## Approach

Honor the already-validated durable 16-reference budget during preflight. Preserve every selected immutable reference or reject incomplete delivery; do not change staffing, trust, or native context/output ceilings. Exercise all five host paths and oversized boundaries.

## Dependencies

AR-404 owns the five-host reliability outcome. AR-423 and AR-426 retain their
native delivery and isolated acceptance gates.

## Acceptance

- [ ] Exact selected-team omission is preserved with session/trace and role evidence.
- [ ] Every inference-selected card is retained or delivery fails explicitly; host limits and load truthfulness remain enforced.
- [ ] Focused, fast and fresh installed native complete-team evidence pass.
