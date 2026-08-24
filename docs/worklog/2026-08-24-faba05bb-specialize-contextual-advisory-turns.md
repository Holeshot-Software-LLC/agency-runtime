---
title: "Worklog detail: specialize contextual advisory turns"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [routing, classification, workforce, safety]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
supersedes: []
superseded_by: null
type: worklog
commit: faba05bbb97f91a87730e3b1e223cf156432d9c2
short: faba05bb
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
---

# Worklog detail: specialize contextual advisory turns

## Purpose

Let short contextual inquiries such as status, progress, recommendations, and
prospective next steps receive a fresh specialist route for the subject already
under discussion without treating the question as permission to execute work.

## Approach

Classifier v5 separates specialist selection and fresh rerouting from execution
authority. It projects the exact preceding substantive same-session turn into a
bounded, transcript-free subject capsule containing governed specialist and
closed typed subject identifiers. Planner and recruiter receive that capsule as
separate untrusted evidence; cache and receipt identities bind its digest.

Advisory plans compile to at most one parent-only `analysis` unit with `advise`
authority and `read_only` mutation scope. The ready transaction reselects the
source turn and rejects source, evidence, recipe, context, or roster drift before
publishing the route. The five-field header remains a receipt of that completed
turn-scoped decision.

## Challenges encountered

The first decision-conformance run could not attest its disposable Windows
scratch directory under restricted process permissions. Repeating the same
repository evaluator with normal host permissions passed its baseline and all
151 curated mutations without changing source.

## Decisions and alternatives

ADR-0163 records the choice to use typed transcript-free context instead of raw
retained user or assistant text. Historical specialists are reranked against the
current eligible roster rather than deterministically reused. Inference-owned
gap hiring remains available as internal workforce mutation, but the advisory
projection cannot grant native-child, workspace-write, or external-write
authority.

## Verification

- Focused classifier, selector, Store, and inference slice: 226 passed.
- Named fast production spine: 806 passed, 20 skipped in 135.02 seconds.
- Dashboard UI: 134 of 134 passed.
- Routing evaluation: all accuracy, latency, and scale gates passed.
- Decision conformance: baseline passed; 151 killed, 0 survived, 0 invalid;
  source unchanged.
- Documentation metadata, policy availability, Ruff check, Ruff format, and
  Git diff hygiene passed before the ledger update.

## Follow-ups

Tracker creation, pull-request publication, hosted checks, and merge remain
pending explicit authorization under AR-265.
