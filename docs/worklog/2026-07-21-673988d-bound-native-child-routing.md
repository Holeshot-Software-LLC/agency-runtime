---
title: "Bound native child routing and expose account models"
status: active
category: worklog
created: 2026-07-21
updated: 2026-07-21
tags: [routing, delegation, providers, dashboard, codex]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/decisions/0078-present-human-routing-evidence-and-abstain-on-noise.md
  - docs/decisions/0079-route-native-children-once-and-bound-unplanned-reroutes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 673988dc7d2c00e469319fb3a91304b4f2bc4c91
short: 673988d
date: 2026-07-21
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/129
related_issues:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
---

# Worklog detail: Bound native child routing and expose account models

## Purpose

Make live Agency selection safe and understandable while preventing a native
host's subagent fan-out from multiplying routing inference calls. Give operators
an account-aware Codex model picker without weakening manual LiteLLM aliases.

## Approach

Keep planned child routing at the parent and pass one-use activations through
the native host. Coordinate genuinely unplanned child routes through durable,
content-free cache, singleflight, concurrency, and parent-budget records. Add
bounded authenticated CLI model discovery, then expose the same configuration
through the CLI wizard and dashboard. Convert internal header codes to stable
human explanations while retaining raw codes in durable receipts.

## Challenges encountered

The complete Windows suite exposed four shared edge cases: new retention tables
needed open-turn guards, generated Hermes calls needed backward-compatible
keyword projection, exact-unit deterministic routing needed to remain distinct
from broad-route abstention, and Codex's sandbox-private test path exceeded
Windows Git/CreateProcess limits. The release-security cluster passed unchanged
under the repository's normal short private runtime.

## Decisions and alternatives

The runtime does not create a shadow worker pool. Codex, Claude, OpenClaw, and
Hermes remain the schedulers, as recorded in ADR-0079. Weak broad heuristic
matches abstain instead of selecting unrelated specialists, as recorded in
ADR-0078. Completed child cache entries remain independently expirable; only an
entry with an active singleflight lease is retained with its parent graph.

## Verification

- Python: 6,945 passed, 35 skipped.
- Dashboard UI: 90 passed.
- Routing, full-roster, and delegation evaluation gates passed.
- Documentation validation passed for 265 files; tracker parity passed for 116 items.
- Ruff check, Ruff format check, and Git diff check passed.

## Follow-ups

Merge, exact installed-runtime activation, and live Codex/dashboard smoke proof
remain tracked by AR-115 and AR-116.
