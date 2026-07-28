---
title: "AR-185: Bind Codex activation verification to a fresh exact proof"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [security, codex, installation, canary, operator-presence]
related:
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/THREAT_MODEL.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - agency_runtime/core/codex_activation_verification.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/operator_presence.py
  - agency_runtime/adapters/hooks.py
  - agency_runtime/cli/install_commands.py
  - tests/test_codex_activation_verification.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-185
priority: p0
tracker_url: null
depends_on: [AR-193]
blocks:
  - AR-119
  - AR-180
---

# AR-185: Bind Codex activation verification to a fresh exact proof

## Problem

The documented resumable command
`agency install --agent codex --verify-activation` was unreachable. The shared
CLI boundary classified it as a generic installation mutation and rejected it
before its handler because no generic operator-presence verifier is available.
Merely exempting the boolean flag would be unsafe: the generic handler would
materialize controls, seed the roster and contractors, manage the dashboard,
and reinstall the adapter before running the canary.

The existing activation helper also accepted `canary_passed=True` followed by
any verified final attestation. A malformed fresh result could therefore reuse
an older attestation instead of proving the current invocation.

## Current state

The parser, presence boundary, and exact verification branch are working. Two
attended refreshes and terminal-TUI approvals established that the installed
hooks route, inject a valid header, and finalize in a normal Codex invocation.
The first fresh probe stayed in the parent; the second reached workforce
routing but semantic planning split the diagnostic into two units. Both failed
the exact activation graph honestly. AR-180 now isolates this activation
measurement from planner variability with a restricted deterministic one-unit
route. The refreshed exact artifact and final live proof remain pending.

## Approach

Give verification a distinct parser-owned internal action and one shared
closed-world predicate. Only the exact Codex verification shape may bypass the
generic installation presence prompt, and the handler rechecks the same
predicate before branching ahead of every generic install dependency.

The branch performs initial exact-install inspection, one bounded
current-profile canary without the hook-trust bypass, and final inspection.
Success requires the fresh canary report, its persisted attestation, and final
inventory to agree on proof digest, trace, profile, host version, plugin
version, install ID, and bundle digest. An older attestation cannot rescue a
failed or malformed attempt.

The canary may replace activation evidence and write nonce-correlated runtime
evidence. It may not change configuration, controls, roster/workforce state,
dashboard service state, adapter files, native registration, or the Codex trust
store. Catalog bootstrap/reconciliation and dynamic gap hiring fail closed in
this exact child environment. Both the coordinator and every spawned hook open
the Store only when the configured database already exists with a current
schema and WAL state; this path cannot create, migrate, or permission-repair
persistent storage.

## Dependencies

ADR-0077 owns behavioral current-profile proof, ADR-0096 owns the persistent
control authority boundary, and ADR-0104 owns the separate attended adapter
refresh. AR-180 owns the final live specialist-activation evidence. Tracker
creation remains pending explicit outward-write authorization.

## Acceptance

- [x] The exact documented verification command reaches one current-profile
  canary without requesting the generic installation presence verifier.
- [x] Every neighboring shape, unknown future public or private flag, copied marker, and
  malformed timeout fails closed before handler mutation.
- [x] Prepared `install --agent codex --no-dashboard` remains a separate,
  attended mutation and cannot overlap activation verification.
- [x] The verification branch cannot load generic install configuration,
  create the install Store, seed controls/roster/contractors, manage the
  dashboard, plan/install/rollback an adapter, reconcile the catalog, or hire a
  workforce gap.
- [x] The activation Store must already be configured, trusted, current, and
  WAL-backed in both the coordinator and spawned hooks; verification cannot
  bootstrap, migrate, repair, or leave an empty race-created replacement.
- [x] Success requires a fresh, current-profile, persisted attestation that
  exactly matches final installed-host inventory; stale proof cannot be reused.
- [x] Exceptions and malformed results fail nonzero with bounded sanitized
  output, followed by final inspection whenever a canary may have started.
- [x] Focused authority, canary, Store, parser, and installer regressions pass
  warning-strict on the implementation checkpoint.
- [ ] The exact installed artifact passes the live current-profile canary after
  the operator-approved Codex hook trust step.

## Implementation evidence

Three independent CLI, security, and functional reviews confirmed the P0
bypass risk and found stale-proof, spawned-hook Store, malformed-output, and
resumable-action gaps. The implementation now binds temporal and proof identity,
propagates existing-current Store mode through the Codex subprocess, opens that
Store with SQLite `mode=rw`, sanitizes projections, and preserves the attended
next action. A 324-test warning-strict focused package passed with 6 expected
platform skips in 30.23 seconds; the dedicated AR-185 file passed 33 tests in
1.81 seconds. Live proof remains a separate exact-artifact checkpoint and must
not be inferred from registration.
