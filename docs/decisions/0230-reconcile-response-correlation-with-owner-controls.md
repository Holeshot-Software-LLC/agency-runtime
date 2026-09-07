---
title: "Reconcile response-correlation acceptance with owner controls"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, security, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0230
type: decision
deciders: [maintainers]
---

# ADR-0230: Reconcile response-correlation acceptance with owner controls

## Context

AR-170's identity, last-good state and accessibility requirements remain useful.
Three remaining correlation defects are repaired at 90654955, with immediate
ledger f1ff818c. Its original criteria 6/7 still demand read-only status and
attended-only maintenance after ADR-0117 restored owner controls. Criterion 9
requires the obsolete universal final-release gate that ADR-0105 replaced.

## Decision

Before isolated review, explicitly reconcile only criteria 6, 7 and 9:

- Keep hidden semantics and asynchronous state truth; require usable owner
  controls and correct draft state, without granting broker write authority.
- Keep skip-link and heading/keyboard checks, but judge maintenance copy against
  actual owner authority, not a removed human-presence ceremony.
- Use focused UI/current coverage floors, named production spine, current
  docs/tracker/metadata/worklog/Ruff/diff and scoped browser evidence. Do not
  reinstate mandatory exhaustive corpus, coverage matrix or hosted dispatch.

Preserve original wording, all other criteria, and the seven-view/six-tab sweep.
Do not retire the useful record or call historical checked boxes current proof.
All nine current criteria need candidate-bound isolated verdicts.

## Consequences

This applies existing decisions, not new credentials or server permissions.
Pure request-bound validators correlate structural errors without committing
unvalidated state. Exact lookup remains an unpaged zero/one-row endpoint;
general collection pagination is unchanged. The browser receipt identifies
source-served private fixtures, not installed/native-host or full WCAG proof.

## Alternatives

- Restore permanently disabled owner controls: conflicts with ADR-0117.
- Delete all response-correlation requirements: leaves reproduced defects.
- Treat the initial fixture timeout as a production failure: the current UI
  intentionally shows retained-state text; corrected assertions use that contract.
- Silently revise the checklist or require exhaustive checks: defeats explicit
  record discipline and ADR-0105's bounded delivery policy.
