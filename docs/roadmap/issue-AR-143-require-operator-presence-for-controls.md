---
title: "AR-143: Require genuine operator presence for persistent controls"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [security, dashboard, browser, cli, controls, user-presence]
related:
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/THREAT_MODEL.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/core/operator_presence.py
  - agency_runtime/cli/main.py
  - agency_runtime/cli/roster_commands.py
  - agency_runtime/core/store/roster.py
  - tests/test_cli_operator_presence.py
  - tests/test_prepared_roster_rollback.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-143
priority: p0
tracker_url: null
depends_on: [AR-128, AR-160, AR-161]
blocks: [AR-180, AR-196]
---

# AR-143: Require genuine operator presence for persistent controls

## Problem

The in-app Browser is model-callable and can operate an existing authenticated
dashboard session. The owner bearer, deterministic confirmation modal, and
generation CAS therefore do not prove a human operator intended a persistent
mutation. Restricted CLI behavior is also an ACL/error outcome rather than one
uniform caller-attestation boundary.

## Current state

The original owner-dashboard vulnerability is now fail-closed: the shipped
browser has no mutation client and every former endpoint rejects both owner and
broker bearers without dispatch. One CLI pre-dispatch guard still covers the
generic persistent-mutation families and deliberately fails closed because it
has no positive production verifier.

One narrower positive slice now exists: on Windows 11 x64 only, exact
`agency roster rollback` is owned by one Store coordinator that prepares the
authoritative rollback, invokes a packaged native Windows consent verifier, and
revalidates the same captured state inside the committing transaction. This is
the first implemented path, not completion of AR-143.

A second exact positive slice now refreshes an existing Codex integration on
Windows 11 x64. It requires the Agency marketplace and Agency plugin to already
be installed, registered, and enabled; it does not bootstrap a missing host,
marketplace, or plugin. The coordinator prepares the exact configuration,
database, runtime-control, managed-target, Codex executable, candidate launcher,
and native inventory state before a non-exporting Windows Hello verification.
It then locks, prepares the entire transaction again, publishes the managed tree
atomically with an exact backup, removes and re-adds only the Agency plugin, and
accepts only exact filesystem, launcher, marketplace, plugin, and policy
postconditions. Bounded compensation restores the exact prior tree and native
state or reports manual recovery required. Registration remains runtime-
unverified until Codex restarts or opens a new task and passes a bound canary.

Every other persistent mutation, fresh Codex bootstrap, Windows on another
architecture, and every non-Windows positive mutation remain unavailable rather
than falling back to a weaker presence signal.

## Approach

Make the dashboard read-only and reject every mutation endpoint for both owner
and broker bearers. Preserve monitoring and diagnostic value without implying
that a modal is user presence. Audit every CLI and host-native mutation entry
under model-facing identities. A positive CLI path must prepare its exact
authoritative mutation before verification, seal the method, resolved resource
identity, payload binding, and every applicable revision/CAS token, obtain one
native verification result, revalidate the sealed state inside the mutation
lock, and commit through the same resource owner exactly once. Its trusted
native prompt must show a bounded human-readable action, exact target,
current-to-target transition, and material consequence. The direct verifier
result is consumed synchronously in that call stack and is never exported as an
authorization bearer.
Deferred input must be read into the prepared mutation before verification.
Secret-bearing payloads must be bound internally without exporting a stable
secret-dependent digest that becomes an offline guessing oracle; the prompt
shows secret presence and effect, never the secret value.
If a future design introduces a transferable capability, it must additionally
be short-lived, audience-bound, single-use, and atomically replay-protected.

For existing Codex refresh, the prepared authority covers the exact config, DB
and generations, runtime control, managed target and parent, current install and
tree, candidate component bytes and launcher-publication plan, Codex executable
and environment, and exact Agency marketplace/plugin inventory. The native
prompt shows the current-to-candidate transaction and recovery consequence.
After Windows Hello, the coordinator acquires its install lock and prepares all
of that state again before atomic publication or native registration mutation.

## Dependencies

AR-128 remains the read-only MCP/broker foundation. ADR-0096 supersedes the
dashboard exception in ADR-0090. AR-160 owns the paired portable and
`win_amd64` artifact contract. AR-161 owns the separately signed delivery
identity and the owner/legal compiler, runtime, SDK, and notice disposition.

## Acceptance

- [x] Every dashboard mutation rejects owner and broker bearers without state change.
- [x] Authenticated browser automation cannot complete a persistent mutation.
- [ ] Every CLI and host-native mutation family has a supported positive path on
  each claimed platform; today all unsupported paths fail closed.
- [x] The first positive path is limited to exact roster rollback on Windows 11
  x64 and remains behind a positively attested operator boundary.
- [x] That path prepares before verification and rejects resource, target,
  payload, or applicable revision/CAS changes inside the committing boundary.
- [x] Its trusted native prompt makes the exact action, target, current-to-target
  transition, and material consequence intelligible without decoding a digest.
- [ ] Future positive paths with deferred stdin or secret-bearing input prepare
  that input before verification and expose neither the value nor a stable
  guessing oracle. Roster rollback has no such input.
- [x] The native result is consumed in the same call stack and never becomes a
  transferable authorization capability.
- [x] Exact existing Codex refresh prepares config, database, control, target,
  executable, candidate plan, and native inventory before verification.
- [x] That Codex path uses the non-exporting Windows Hello verifier, then locks
  and prepares the complete transaction again before mutation.
- [x] Codex refresh atomically publishes the managed tree with an exact backup,
  removes and re-adds only the Agency plugin, and requires exact postconditions.
- [x] Post-publication failure uses bounded identity-checked compensation and
  never claims complete restoration without the exact prior tree and inventory.
- [x] The positive Codex path refuses fresh missing-host, missing-marketplace,
  absent-plugin, disabled-plugin, and ambiguous-inventory bootstrap shapes.
- [ ] A restarted or new Codex task passes a capability- and installation-bound
  canary for the exact refreshed candidate; registration alone is not loading.
- [ ] AR-160 proves the paired portable and `win_amd64` artifact set without a
  Windows PE payload in the unrestricted wheel.
- [ ] AR-161 records owner-authorized publisher identity, independent signed-
  artifact verification, and authorized legal disposition for the exact MSVC,
  Windows SDK, static runtime, and upstream notices.
- [ ] An attended Windows Hello success-and-denial canary passes from the exact
  signed Windows release candidate. The unsigned existing-Codex refresh is
  local dogfood evidence, not this release gate.

The general contract remains that deferred stdin/prompt input is prepared
before verification. Secret payload binding exposes neither the value nor a
deterministic guessing oracle. Any future transferable capability also rejects
missing, expired, replayed, and audience-mismatched use atomically.

## Implementation evidence

The dashboard JavaScript contains no mutation client or actionable mutation
controls, and every former mutation endpoint rejects both owner and broker
bearers without dispatch. A single CLI pre-dispatch guard covers every
persistent mutation family. Exact roster rollback is marked as a prepared
operation and bypasses that generic unavailable verifier only to enter the
Store-owned rollback coordinator; it cannot dispatch through the old direct
mutation path.

The coordinator captures an exact immutable tuple of built-in primitive values:
configuration and database lexical/file identities, roster generation, slug,
the complete current projection identity, target revision identity and digest,
activation-authority kind and digest, and workforce/effective-contract digest.
No public prepare or commit API exists, no verifier dependency or boolean can be
supplied by the caller, and the native verifier returns no receipt. After the
native result, the coordinator compares the same tuple and begins an immediate
transaction on the same Store. It then rechecks every captured identity before
applying the target once; a denial, replay, substitution, race, or apply failure
leaves the rollback effects uncommitted.

Target authority is not inferred from version/hash alone. Bundled targets bind
the exact packaged manifest and revision. Governed snapshot targets bind the
candidate, approved and activated audits and status events, snapshot record,
and approval/activation import events. Workforce validation binds either
explicit absence or the complete ordered target recruitment-contract projection
chain. That chain is capped at 1,024 records using the shared 8 KiB contract
limit, must descend hash-by-hash from the target lineage, must use exact
`agency-runtime-package` authority, and validates every contract's hash,
worker, agent, target version/hash, and origin. An absent eligible upstream
lineage binds the deterministic contract that commit will generate. Restoring a
historical routing/workforce contract preserves the worker's current employment
and standing.

The packaged x64 GUI helper owns an app window and uses
`IUserConsentVerifierInterop::RequestVerificationForWindowAsync`. The bounded
ASCII protocol binds action, slug, current and target version/hash, authority,
and a fresh nonce. Only the exact nonce-bound verified result with exit zero,
empty stderr, and no timeout, cancellation, truncation, or containment failure
continues. Source, provenance, and executable bytes are pinned and revalidated
from an owner-private installed namespace; availability checks never authorize.
The success transaction records sanitized target revision, authority,
workforce, verifier mechanism, and pinned-helper provenance, but never the
nonce, stdout, native result, or a receipt.

Tests cover absent and malformed authority, target and workforce drift, complete
one- and two-step projection chains, arbitrary projection authority, broken
parents, explicit projection absence, append-after-prepare, lifecycle overlays,
denial, cancellation, malformed native results, post-verification substitution,
replay, same-Store ordering, and atomic rollback after injected failure.

The existing-Codex refresh coordinator separately captures one immutable
binding over configuration, database and control generations, the complete
managed target, candidate transaction plan, exact Codex executable/environment,
and exact marketplace/plugin inventory. The dedicated native prompt uses the
same pinned non-exporting Windows verifier. Under the install lock, the
coordinator prepares that full binding again, publishes a content-addressed
private launcher and atomically swaps the managed tree, proves the native
remove/add transition, and validates exact filesystem, launcher, inventory,
version, enabled, source, install-policy, and authorization-policy
postconditions. Failure compensation is compare-and-swap bounded to the frozen
candidate and backup and claims success only after exact prior target and native
state equality. Same-version repair is intentionally valid because bundle and
registration drift can exist without a version change.

## Remaining release and scope gates

- On 2026-07-27, exact local candidate `6d55e29` was built from a clean detached
  worktree into a fresh owner-private Python 3.13 environment. The 7,403,575-
  byte `win_amd64` wheel (`7d071c8c...593f0`) and 17,993,098-byte sdist
  (`3a81eddf...e316`) passed strict metadata and independent distribution
  verification. A fresh wheel venv passed version and real Codex status smoke.
  The first non-visible Windows verification attempt failed safely before
  mutation. A second taskbar-visible attempt completed Windows Hello and the
  exact transaction with exit zero. Status then proved new install ID
  `7761d792-3dc3-4c92-8084-5cd524c63103`, bundle
  `0c3696e1...084f3`, retained backup `20260727T160533.282423Z`, and native
  plugin `0.1.0+codex.a106953cb0c7` installed and enabled with exact
  `AVAILABLE`/`ON_INSTALL` policies.
- That attended success proves existing-install publication and registration,
  not activation. After renewed exact hook trust, a fresh Codex process proved
  the Agency header, routing, expected specialist selection, delegation plan,
  and Stop finalization. It correctly rejected the turn because isolated child
  activation was absent. AR-180 owns that now-reproduced canary gap; no
  attestation was persisted.
- The admitted Codex transaction is deliberately existing-only. Missing-host,
  missing-marketplace, absent-plugin, disabled-plugin, or ambiguous-inventory
  states still fail before Windows Hello and require a separately reviewed fresh
  bootstrap design.
- Filesystem publication and native registration do not prove activation. Codex
  must restart or open a new task, and that task must pass the capability- and
  installation-bound canary before loaded, hook-trusted, or production-ready
  claims are allowed.

- The helper is a reviewed but unsigned Windows executable. AR-161 and
  ADR-0099 keep reproducible unsigned review bytes separate from signed
  delivery bytes. No approved publisher identity, signature, or legal
  compiler/runtime/SDK entitlement is claimed yet.
- ADR-0098 selects a paired portable plus `win_amd64` wheel architecture, but
  AR-160 remains in progress. The source now implements host-derived producer
  pairs and an independent three-artifact merge verifier; hosted Windows/Linux
  producer and merge proof remains unavailable while Actions billing is
  disabled.
- A real attended Windows Hello success-and-denial roster-rollback canary has
  not run. The existing-Codex refresh success above does not satisfy that
  separate mutation or the signed release-candidate gate.
- Linux, Windows ARM64, fresh Codex bootstrap, and every persistent mutation
  other than exact roster rollback and exact existing-Codex refresh remain
  deliberately unavailable.
- The trusted operating-system account and Python interpreter remain inside the
  trust boundary. Same-account code replacement, monkeypatching/private
  reflection, debugger access, or raw SQLite writes are not defeated by a
  Python coordinator and require stronger process/package policy.

AR-143 therefore remains open. This evidence supports two reviewed positive
slices; it does not support fresh Codex bootstrap or a generic production-ready
claim. The helper is still unsigned, signing and legal disposition remain
blocked, and activation still requires restart/new-task canary evidence.
