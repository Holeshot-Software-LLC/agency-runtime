---
title: "Reconcile dashboard disclosure with current owner authority"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, security, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0229
type: decision
deciders: [maintainers]
---

# ADR-0229: Reconcile dashboard disclosure with current owner authority

## Context

AR-166 criterion 1 still requires read-only persistent dashboard controls under
superseded ADR-0096. ADR-0117 deliberately restored owner controls without
granting broker, hook or MCP credentials write scope. Most controls follow that
policy, but the provider-secret selector still disables every nonempty list.
Owners cannot choose a different provider for a key edit or removal.

AR-298 replaced the old 8192-character preview with complete bounded Store-backed
definitions. Current dashboard detail requests at most 262144 characters and
labels stored definitions separately from runtime proof.

## Decision

Explicitly replace only AR-166 criterion 1 before isolated review:
owner-authorized provider choices remain usable after rendering; empty,
non-array or unparseable provider lists stay disabled, stored keys are not
reflected, and broker write scope remains unchanged.

Preserve its original wording and the other five criteria. Apply ADR-0117's
existing authority, not a new permission exception. Repair only the stale
selector assignment and tests. Backend authentication, confirmation/revision
safeguards and broker denial stay unchanged.

Describe AR-298's current bounded definition accurately without changing
criterion 5 or asserting runtime delivery. AR-298's broader acceptance remains
its own; this record neither completes that issue nor restores the short preview.

## Consequences

Owner selection survives re-render; invalid list state disables it and valid
recovery restores it. No credentials or server permissions are granted.
All six current criteria require isolated candidate-bound verdicts.

Selector implementation and initial evidence: a4be59b0, with immediate ledger
ebb471a8. Acceptance verdicts follow the final candidate, not this decision.

## Alternatives

- Disable the whole dashboard: rejected as contrary to ADR-0117.
- Retire the whole record: rejected; correlation/privacy still matter and the
  stale selector restriction is a current observable defect.
- Restore the short preview: rejected as contrary to AR-298.
- Silently edit acceptance: rejected; original wording and reasoning remain.
