---
title: "Separate reversible agent availability from governed roster state"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-17
tags: [agents, roster, configuration, routing, operations]
related:
  - docs/roadmap/issue-AR-28-reversible-agent-activation-controls.md
  - docs/roadmap/issue-AR-75-broker-restricted-windows-agent-controls.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0033-explicit-companion-route-availability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0046
type: decision
deciders: []
---

# ADR-0046: Separate reversible agent availability from governed roster state

## Context

Roster activation means a source was reviewed and its immutable specialist
definition was approved for local use. Operators also need a lighter-weight way
to narrow a large approved roster for cost, focus, or preference. Deleting an
active row or activating a replacement snapshot for that preference would mix
two different concerns, discard useful state, and make restoration cumbersome.

The bundled no-match contract depends on `agents-orchestrator` and
`chief-of-staff`. Allowing either coordinator to be disabled would recreate the
starter-install failure that the fallback policy is designed to prevent.

## Decision

Store reversible operator availability in the shared typed configuration as a
bounded canonical `agents.disabled` slug set. The default is empty: every
governed roster definition is enabled unless the operator explicitly disables
it. Configuration writes remain locked, revision-checked, validated, atomic,
and portable across Windows and Linux.

Keep roster definitions, immutable prompt versions, snapshots, and provenance
unchanged while an agent is disabled. Exclude disabled agents from new routing,
search, public roster projections, and direct active-prompt loads. Management
views may show preserved disabled rows so the operator can re-enable them. An
already-correlated turn and its immutable audit evidence are not rewritten, but
disablement immediately invalidates replay, activation-token preparation or
consumption, and affected ready-turn completion. The work must re-enter
selection under current policy instead of finishing with a now-disabled
definition.

Treat `agents-orchestrator` and `chief-of-staff` as protected invariants. Reject
either slug in `agents.disabled` during typed-document validation and raw config
loading, reject disable mutations before writing, and treat the coordinators as
enabled at the runtime projection boundary. Unknown, malformed, duplicate, and
oversized slug sets fail validation rather than being partially applied.

Expose the same policy through a small CLI and authenticated dashboard quick
controls. Bulk list pages expose only bounded activation fields; a separate
authenticated exact-slug lookup reaches one governed agent beyond the
dashboard's first page without exporting the complete selector catalog or
increasing response and DOM bounds. Dashboard mutations require the current
config revision and an exact operation-specific confirmation phrase; neither
surface owns a second state store. The toggle repeats roster membership,
confirmation, effective disabled-set, and active Store-binding checks inside
the config writer lock after revision validation.
Runtime reads cache the parsed activation policy against the config path, file
identity, timestamps, size, and relevant environment overrides. An atomic write
from any process changes that signature, so the next routing read refreshes the
policy without repeatedly parsing YAML during one unchanged preflight.

## Consequences

- Operator preference no longer mutates or deletes governed roster data.
- Re-enabling is an atomic config change and restores the existing definition.
- Routing, search, prompt loads, CLI, HTTP, MCP, and dashboard counts share one
  effective availability boundary.
- The default fallback pair cannot be removed accidentally or through a hand-
  edited configuration file.
- Dashboard management endpoints distinguish total governed definitions from
  the smaller enabled routing roster.
- Config updates take effect without a schema migration or host reinstall.
- Concurrent config and roster changes cannot redirect an agent toggle after
  its revision check.
- Repeated selector and prompt reads do not put YAML parsing on the routing hot path.

## Alternatives

- Delete disabled agents from `agent_active`. Rejected because it destroys the
  approved local roster projection and entangles preference with governance.
- Store an `enabled` bit beside each roster row. Rejected because snapshot
  activation could overwrite operator preference and would require a database
  migration for a user-scoped configuration concern.
- Persist an allowlist instead of a denylist. Rejected because newly approved
  agents should be enabled by default and an allowlist would require continual
  manual reconciliation.
- Permit disabling the fallback coordinators with a warning. Rejected because a
  warning cannot preserve the deterministic no-match runtime contract.
