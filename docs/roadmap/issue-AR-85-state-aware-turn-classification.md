---
title: "AR-85: Replace generic triviality with state-aware turn classification"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-08-24
tags: [routing, lifecycle, correlation, inference, compatibility]
related:
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-85
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/86"
depends_on: [AR-25]
blocks: [AR-265]
---

# AR-85: Replace generic triviality with state-aware turn classification

## Problem

Agency historically projected user turns into a generic `trivial` or
`nontrivial` bit using short-message heuristics and a configurable character
threshold. That boundary is too generic for contextual replies: `yes`,
`continue`, `ship it`, and even a short request such as `fix auth` can carry
substantive intent. It also couples the question of whether expertise would
help to the separate question of whether native delegation is warranted.

## Current state

The runtime now emits a versioned, content-free classification with one of six
turn kinds: acknowledgement, conversation, control, continuation, new intent,
or revision. It evaluates durable prior-turn state and separately records
whether specialist selection, rerouting, and an execution decision are
required. Missing, stale, ambiguous, or corrupt state fails closed. The old
trivial/nontrivial fields remain only as compatibility projections and the
configured character threshold is inert with a consistent zero default.

One clean-state conversation escape hatch still bypassed roster consideration;
that mismatch was removed so only a proven pure acknowledgement, plus an exact
runtime control handled by its dedicated control path, can avoid specialist
selection.

The authority boundary is now durable and turn-scoped. Current classifier
objects are process-sealed to the exact raw message and must satisfy a strict
kind/boolean/correlation matrix. Adapter origins are separately process-sealed
to an allowlisted host lifecycle event and exact session/turn correlation.
Prompt text cannot claim retry, Stop, continuation, or child origin.

## Approach

Keep turn intent, expertise selection, and execution topology as three explicit
decisions. Derive continuation meaning from durable correlation, open work,
pending questions or authorization, retry state, specialist revisions,
configuration revision, roster revision, and delegation state. Reuse a prior
plan only when every guard remains current; otherwise reroute the affected work.

Preserve the legacy `trivial` boolean and request-kind string only at old API
and storage boundaries while making the typed classification authoritative.
Expose the complete bounded projection through host and HTTP preflight
surfaces. Do not use prompt length as an authority boundary.

Parse runtime controls once across every surface. Resolve pending questions and
authorizations before contextual-token reuse. Revalidate continuation guards
again in the ready transaction and perform at most one fresh reroute when a
source recipe, specialist revision, work-unit plan, or commit-time guard is no
longer current. Internal lifecycle events reuse or revalidate their existing
turn and never call fresh preflight.

## Dependencies

AR-25 supplies the turn-scoped correlation and durable evidence needed to
classify a contextual reply safely. ADR-0045 remains authoritative for
specialist activation lifetime; ADR-0064 owns the new intent-classification
boundary.

## Acceptance

- [x] Every external turn has exactly one of the six documented turn kinds.
- [x] Turn intent, specialist selection, rerouting, and execution decisions are separate fields.
- [x] Short substantive requests cannot bypass selection because of length.
- [x] Only a proven pure acknowledgement may use the no-selection path; exact runtime controls use their dedicated control path.
- [x] Pure social conversation remains a distinct kind but still considers the approved enabled roster.
- [x] Contextual replies use durable pending-work, question, authorization, retry, and revision state.
- [x] Missing, stale, ambiguous, and corrupt state fail closed.
- [x] Continuation reuse is guarded by correlation, config, roster, specialist, and delegation revisions.
- [x] Pending question and authorization replies reroute before contextual-token reuse.
- [x] Invalid or raced continuation guards perform one bounded fresh route instead of manager abstention.
- [x] Public routing rejects forged, cross-message, and unsupported-version classifier objects.
- [x] Adapter origins are process-sealed and prompt content cannot authenticate an internal retry.
- [x] Runtime-control parsing is identical across classifier, CLI, host executor, and generated host guidance.
- [x] `trivial_msg_threshold` is not an authority boundary and every default source agrees on zero.
- [x] Legacy trivial/nontrivial fields are compatibility projections only.
- [x] HTTP preflight exposes the bounded typed and resident-manager projection.
- [x] Full Python, dashboard, routing, documentation, installed-host, and tracker gates pass on the final tree.

The final PR #114 tree passed exact line and branch coverage, every hosted
Python cell, dashboard UI tests, routing/delegation/full-roster evaluation,
artifact smoke and parity, documentation validation, and both installed Codex
control modes. Tracker reconciliation is completed with this final ledger PR.
