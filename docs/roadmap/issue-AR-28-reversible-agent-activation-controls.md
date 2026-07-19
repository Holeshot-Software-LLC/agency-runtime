---
title: "AR-28: Add reversible per-agent activation controls"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-18
tags: [agents, roster, configuration, cli, dashboard, routing]
related:
  - docs/decisions/0046-config-backed-agent-activation-policy.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-28
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/29"
depends_on: []
blocks: [AR-36, AR-75, AR-83, AR-86, AR-89, AR-91]
---

# AR-28: Add reversible per-agent activation controls

## Problem

An approved roster can contain hundreds of governed specialists, but operators
cannot quickly remove an unneeded specialist from routing without changing or
deleting roster state. Deactivation through roster mutation would lose the
distinction between governance approval and local runtime preference and make a
later re-enable unnecessarily destructive.

## Current state

Roster snapshots remain durable governance data while one bounded typed
`agents.disabled` set controls reversible operator availability. CLI and
dashboard mutations share the same revision-checked configuration writer;
routing, search, public roster projection, activation preparation, token
consumption, and ready-turn completion all enforce it. Disabled definitions
remain intact, and schema plus runtime invariants prevent either protected
fallback coordinator from being disabled.

## Approach

Add a bounded `agents.disabled` set to the shared typed configuration. Keep it
empty by default so every governed agent starts enabled. Filter disabled agents
from new routing, search, public roster, and direct prompt-load paths while
retaining their roster rows and immutable prompt versions. Expose a concise
`agency agents list|enable|disable` CLI and authenticated dashboard toggles that
use the existing revision-checked atomic configuration writer. The dashboard
also provides a bounded exact-slug lookup so an operator can reach definitions
beyond the first 1,000-row response without expanding response or DOM bounds.
Use a file-identity-aware configuration cache so repeated catalog and prompt
reads share one policy snapshot while atomic edits made by another CLI or
dashboard process invalidate immediately. Reject attempts to disable
`agents-orchestrator` or `chief-of-staff` at schema, direct-file,
CLI, dashboard, and runtime boundaries.

## Dependencies

This extends ADR-0006's shared configuration boundary, preserves ADR-0013's
governed roster state, and uses ADR-0029's authenticated dashboard mutation
contract. It does not replace roster approval or snapshot activation.

## Acceptance

- [x] All governed agents are enabled by default.
- [x] A bounded typed configuration set persists disabled non-default slugs.
- [x] Raw configuration cannot disable either protected coordinator.
- [x] CLI list, enable, and disable commands share the atomic config writer.
- [x] Authenticated dashboard cards show state and provide quick toggles.
- [x] Exact-slug lookup reaches and toggles agents beyond the first 1,000 rows.
- [x] Dashboard quick controls retain the latest configuration CAS revision.
- [x] Routing, search, public roster, and new prompt loads exclude disabled agents.
- [x] Disabled definitions and prompt versions remain intact and re-enable cleanly.
- [x] Unchanged activation policy is parsed once and external config writes invalidate the cache.
- [x] Inputs, config revisions, authentication, and confirmation phrases are validated.
- [x] Focused Python and dashboard UI tests pass on the current Windows tree.
- [x] Full repository validation and tracker synchronization pass.
