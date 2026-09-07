---
title: "AR-185: Bind Codex activation verification to a fresh exact proof"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [security, codex, installation, canary, owner-authority]
related:
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/roadmap/acceptance/issue-AR-185.md
  - docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/roadmap/handoffs/issue-AR-185.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/THREAT_MODEL.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - agency_runtime/core/codex_activation_verification.py
  - agency_runtime/core/canary_backends.py
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
depends_on: [AR-193, AR-195, AR-197]
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

September 7 reconciliation: the exact verification-only CLI branch is
implemented and has current installed evidence. The September 7 22:04:41Z
current-profile Codex CLI 0.153.4 invocation returned success, attempted no
installation, used no hook-trust bypass, and persisted a fresh installation-bound
v4 attestation. AR-180's committed read-only correlation connects that same
invocation to a host-written pre-speech v6 card, one completed native child, and
the parent's accepted finalization. The ongoing review session is not thereby
staffed, and AR-180's broader TUI/Desktop/multi-card criteria remain separate.

The July deterministic-route description is historical, not current behavior.
The restricted probe now uses inference-owned selection, requires one exact
read-only diagnostic unit and provider evidence, and does not enter gap hiring.
Fresh Linux-focused checks pass 274 tests; 40 Windows-specific cases are
excluded. All 328 installed Python modules match the pinned hook runtime;
verification-path source identity, the limited differences from current main,
commands, results, and all nine criterion mappings are in the linked receipt.

ADR-0117 authorizes normal owner CLI mutations without a second Agency-owned
human-presence ceremony. Criterion 3 is explicitly corrected from "attended
mutation" to "owner-CLI prepared mutation"; its original wording is retained
in the receipt. Exact preparation, locked revalidation, ownership, compensation,
and independent activation proof remain required. Criterion 2 is explicitly
scoped to the exact no-bypass verification-only slice; the supported autonomous
and managed-policy modes remain distinct under ADR-0173. Its original wording
is also preserved. No new native trust approval occurred in this package: the
successful no-bypass canary used already-trusted
definitions. Historical checked boxes are preserved, the final box remains
unchecked pending isolated verification, and this issue remains in progress.

## Approach

Keep the parser-owned verification action and closed-world shape predicate.
The handler validates that shape before branching ahead of every generic
install dependency. Unknown public/private fields and neighboring install
forms cannot fall through into the verification-only slice. This is operation
separation under owner CLI authority, not an exception to a retired generic
presence prompt.

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

ADR-0117 governs owner CLI authority. ADR-0104 retains the prepared refresh's
transaction and compensation design; its earlier native-presence prescription
is not the current authority policy. ADR-0077 and ADR-0096 are historical
superseded records, not authority to restore deterministic staffing or an
Agency-owned presence verifier. ADR-0179 and ADR-0193 govern the restricted
native delivery proof and compatible current host version. AR-180 owns the
underlying live receipt and its broader unresolved delivery coverage. The
historical AR-193/195/197 dependency links do not turn Linux evidence into a
Windows claim. This pre-tracker record still has no tracker URL.

## Acceptance

- [x] The exact documented verification command reaches one current-profile
  canary without requesting the generic installation presence verifier.
- [x] For the exact no-bypass verification-only slice, every neighboring shape,
  unknown future public or private flag, copied marker, and malformed timeout
  fails closed before handler mutation.
- [x] Prepared `install --agent codex --no-dashboard` remains a separate,
  owner-CLI prepared mutation and cannot overlap activation verification.
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

Historical July implementation evidence: three CLI, security, and functional
reviews confirmed the P0 bypass risk and found stale-proof, spawned-hook Store,
malformed-output, and resumable-action gaps. That implementation bound temporal
and proof identity, propagated existing-current Store mode through the Codex
subprocess, opened that Store with SQLite `mode=rw`, sanitized projections, and
preserved the then-attended next action. A 324-test warning-strict focused package
passed with 6 expected
platform skips in 30.23 seconds; the dedicated AR-185 file passed 33 tests in
1.81 seconds. Those totals are historical. Current evidence and its exact scope
are in the September 7 receipt; live proof is not inferred from registration.
