---
title: "AR-426: Preserve Hermes specialist context across native hook spilling"
status: blocked
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

Callback source faf5645a, canonical artifact source 22f24edd, is installed;
616 package files match. Focused 131, production 1151 passed / 3 skipped,
UI 224 and conformance 188/188 pass. Recipe 18 delivers bounded card fragments
through ordered native callbacks before the model runs.

The first tool-only phase failed all three full acceptance gates: models skipped
retrieval. The second callback phase never reached card delivery: ordinary review
failed coverage/confidence verification, follow-up received a critic veto, and
multi-step timed out at the planner after 60 seconds. All six failed gates remain
in the two native evidence JSONs; none is reopened or manually finalized.

The one fresh post-timeout attempt took 91.605 seconds and failed a critic veto,
with a rejected reranker contract also retained. It has no finalization events.
No further attempt is scheduled. Native full-card/header/finalization proof is
absent. AR-426 is blocked by shared staffing; PR 824 remains draft and unmerged.

The actual Hermes checkout is 7cd91114b462b7af76e558cc4e97f82201d2e884;
its default hook spill threshold remains 10,000 characters. AR-418's separate
output truncation limit and upstream adoption remain unproven.

Two isolated passes accepted the guarded delivery criterion; the baseline
preservation criterion remains absent in its frozen packet, and native acceptance
is explicitly absent. Exact saved missing-context files are now retained for a
future corrected packet. The owner has now authorized one additional isolated pass; it is reserved until
the next native evidence packet is ready.

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

- [ ] Exact native pointer substitution and missing context are preserved.
- [ ] Bounded native delivery returns exact selected cards with truthful loads;
      missing, cross-turn, unselected and oversized requests cannot invent loads.
- [ ] Focused and required fast checks plus fresh installed native evidence prove
      full cards, five matching headers and authoritative finalization.
