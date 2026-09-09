---
title: "AR-426: Preserve Hermes specialist context across native hook spilling"
status: done
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [hermes, context, reliability]
related:
  - docs/worklog/2026-09-09-hermes-context-spill.md
  - docs/decisions/0244-deliver-large-hermes-card-sets-through-native-tools.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-426
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
depends_on: []
blocks: []
---

# AR-426: Preserve Hermes specialist context across native hook spilling

## Problem

Native Hermes replaces plugin context above 10,000 characters with a 500-character
head and tail. The fixed follow-up and multi-step contexts were 12,991 and 16,585
characters; native messages 535347 and 535352 contain pointers rather than full
cards or the response contract. Store nevertheless records the inline cards as
loaded. Both first responses fail header validation and remain terminal failures.
This input-context defect is distinct from AR-418 output truncation.

## Current state

All three isolated criteria are satisfied in `acceptance/issue-AR-426.md`.
AR-426 used the owner-authorized third pass; AR-427 used its first pass.
PR 824 merged at `e81f8e00`; tracker closure is complete. Earlier failed native receipts remain failed.


Recipe 19 source `176adc19`, artifact source `20c49e0d`, is installed; all 616
package files match. Focused 66 passed / 1 skipped, production 1151 / 3 skipped,
UI 224 and frozen conformance 188/188 pass. Existing source `faf5645a` delivers
bounded fragments through ordered native callbacks before the model runs.

Fresh Hermes session `20260909_143551_e08888` passed in 114.863s. Native message
535391 retains all five inference-selected immutable cards, response contract and
delivery rules without a spill pointer. All five headers match Store and the
first authoritative accepted response hash is
`6546ecb6525a7f1237f47e519b7971574e9d7424862bf50e23ee364f9a980968`.
Exact context, cards and terminal receipts are in AR-427 evidence. The authorized
third isolated pass satisfied all criteria; earlier two records are retained.

The original tool-only and callback-phase failures, the post-timeout critic veto
and the new captured critic veto remain failed. The last capture revealed a real
planning concern recorded as AR-428; no critic is bypassed or treated as erroneous.

Hermes checkout remains `7cd91114b462b7af76e558cc4e97f82201d2e884` with its
10,000-character per-callback spill threshold unchanged. AR-418's upstream
terminal patch is still open and the original output cap remains unknown.

## Approach

Keep a bounded hook frame and deliver large selected card sets through ordered
native callbacks using the guarded local retrieval operation, bound to the active
session and trace. Resolve only selected immutable
versions, record loads after the full bounded result is built, and fail oversized
results without claiming delivery. Preserve first-pass finalization and all
staffing/critic gates. Verify source regression, installed files and fresh native
full-card/header/terminal evidence before claiming acceptance.

## Dependencies

ADR-0244 governs native tool delivery. AR-404 retains five-host reliability;
AR-418 retains the separate upstream terminal lifecycle and original output cap.

## Acceptance

- [x] Exact native pointer substitution and missing context are preserved.
- [x] Bounded native delivery returns exact selected cards with truthful loads;
      missing, cross-turn, unselected and oversized requests cannot invent loads.
- [x] Focused and required fast checks plus fresh installed native evidence prove
      full cards, five matching headers and authoritative finalization.
