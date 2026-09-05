---
title: "AR-116: Bound native-child routing and add account-aware model selection"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [routing, delegation, providers, dashboard, cli]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - README.md
  - agency_runtime/core/store/child_routing.py
  - agency_runtime/core/cli_transport.py
  - docs/decisions/0079-route-native-children-once-and-bound-unplanned-reroutes.md
  - docs/roadmap/issue-AR-118-reconcile-native-child-activation-evidence.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-116
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/128
depends_on: []
blocks: [AR-118, AR-119]
---

# AR-116: Bound native-child routing and add account-aware model selection

## Problem

A host may create hundreds of native children. If every unplanned child runs an
independent model-based Agency selection, the host's own concurrency can amplify
cost and latency. Operators using a Codex subscription also need a safe way to
choose a cheaper visible model instead of guessing model IDs. Manual LiteLLM
router aliases must remain supported.

## Current state

Parent-planned work units already carry exact one-use specialist activations,
but unplanned children have no shared inference budget or cross-process
singleflight. CLI providers accept a model override, while the setup wizard and
dashboard do not discover the models visible to the signed-in account.

## Approach

Keep native hosts in charge of scheduling. Route planned units once in the
parent and let each child consume its exact activation without another routing
call. Correlate unplanned children to their parent and coordinate an expiring
content-free cache, singleflight lease, inference budget, and concurrency limit
through SQLite. When configured inference cannot run within that budget,
abstain instead of claiming a heuristic specialist.

Discover Codex subscription models through the authenticated CLI, project only
bounded public metadata, and offer the result in the setup wizard and dashboard.
Keep a manual field for CLI model IDs and LiteLLM router/model-group aliases.

## Dependencies

AR-115 is now retired under ADR-0222; it is retained as historical provenance,
not an active prerequisite to this already-recorded transport implementation.
The original dependency statement below does not reauthorize heuristic staffing.

AR-115 establishes trustworthy routing output and weak-signal abstention.
ADR-0070 defines child-specific native activation and ADR-0067 keeps configured
inference authoritative for specialist selections.

## Acceptance

- [x] Planned native children consume parent-issued one-use activations with no child inference.
- [x] Unplanned children share durable parent budgets, concurrency, cache, and singleflight state.
- [x] Budget or concurrency exhaustion abstains rather than claiming model-selected expertise.
- [x] Parent correlation is carried by Codex, Claude, OpenClaw, and Hermes adapters.
- [x] Codex account-visible models are available from the CLI and dashboard.
- [x] The guided CLI offers discovered subscription models and a manual fallback.
- [x] LiteLLM router aliases remain first-class manual configuration values.
- [x] Consumed child activation and parent delegation evidence reconcile without a Stop-hook retry loop.
- [x] Full repository, hosted CI, merge, reinstall, and live Codex smoke gates pass.

The two formerly stale boxes are reconciled by AR-204's later exact installed
Codex product proof. This acceptance records the historical transport only; it
does not satisfy the current host-artifact Rule-4 contract.
