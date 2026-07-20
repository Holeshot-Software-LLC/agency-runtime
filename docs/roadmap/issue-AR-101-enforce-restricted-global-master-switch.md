---
title: "AR-101: Enforce the global master switch in restricted host consumers"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-20
tags: [operations, windows, security, runtime-control, routing]
related:
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-76-restricted-windows-cli-read-and-fail-safe.md
  - docs/roadmap/issue-AR-99-dashboard-broker-materialized-master-control.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-101
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/102"
depends_on: []
blocks: []
---

# AR-101: Enforce the global master switch in restricted host consumers

## Problem

In restricted Windows Codex, global off persisted and status reported disabled,
but CLI search still returned routed agents. The sandbox reader correctly
rejected a same-user control path that the restricted process could mutate;
`master_enabled()` then failed enabled without consulting the authenticated
dashboard, so host consumers could ignore the intentional off state.

## Current state

The installed smoke reproduced ten search results while the authoritative
master state was false, then restored master state to enabled. Canonical
restricted consumers now use one broker-aware authoritative snapshot per
operation. A real restricted off/on cycle bypassed search, route, and
delegation while disabled, then restored normal selection at the next
generation. Hosted Windows/Linux proof remains.

## Approach

Keep the integrity-proving reduced reader first. For the canonical default
identity only, obtain a strictly validated master document from the
authenticated local dashboard when restricted path validation is unavailable.
Never broker an explicit or custom identity. Missing, unreachable, malformed,
or unauthenticated service evidence remains fail-enabled for enforcement and
diagnostically visible. When the prior authoritative read was brokered, apply
the generation-checked mutation through that same broker.

## Dependencies

AR-57 defines the master switch. AR-76 defines restricted CLI behavior. AR-99
fixes the broker’s own strict read. ADR-0053 and ADR-0060 require fail-enabled
integrity without silently ignoring a valid authenticated control state. This
correction can be verified independently.

## Acceptance

- [x] Canonical restricted consumers use validated dashboard state when local integrity proof is unavailable.
- [x] Custom identities are never redirected and unavailable or malformed brokerage stays fail-enabled.
- [x] Restricted global mutation uses the dashboard after a brokered authoritative read.
- [x] Off bypasses search, route, preflight, delegation, model, and finalization work.
- [x] On restores normal behavior and the installed restricted Codex smoke passes.
- [x] The full suite and hosted Windows/Linux gates pass.
