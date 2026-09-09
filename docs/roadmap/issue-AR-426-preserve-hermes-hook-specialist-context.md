---
title: "AR-426: Preserve Hermes specialist context across native hook spilling"
status: in_progress
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

Callback candidate sourcefaf5645a/artifact22f24edd is installed with616exact file
matches. Focused131, production1151/3skip, UI224, conformance188/188 and canonical
build/independent artifact/smoke checks pass. Fresh native proof follows once per
fixed manifest case; initial tool-only failures remain preserved.

First native tool-only phase failed all three full acceptance gates. Intact frames
arrived, but the model skipped card retrieval. Recipe18 refines delivery through
ordered per-card native callbacks and a final current snapshot; revised focused
and fast validation/install/demo are pending. Prior failures are preserved.

Recipe18 candidate implemented;75context/terminal tests pass. Fast production1151/3skip, UI224, conformance188/188 and canonical616file install
pass. Native proof and isolated acceptance remain pending. Exact baseline is
evidence/AR-426-exact-native-spill-and-terminal-audit-20260909.json.

Scoped from the exact retained AR-404 receipts. Installed native checkout is
7cd91114b462b7af76e558cc4e97f82201d2e884; its default spilling is enabled at
10,000 characters. No budget, permission, selection or old receipt is changed.

## Approach

Keep a bounded hook frame and deliver large selected card sets through a native
local tool bound to the active session and trace. Resolve only selected immutable
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
