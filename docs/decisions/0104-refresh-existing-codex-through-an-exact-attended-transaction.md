---
title: "Refresh existing Codex through an exact attended transaction"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-28
tags: [security, codex, installation, user-presence, transactions]
related:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - agency_runtime/core/prepared_codex_install.py
supersedes: []
superseded_by: null
id: ADR-0104
type: decision
deciders: [maintainers]
---

# ADR-0104: Refresh existing Codex through an exact attended transaction

## Context

ADR-0096 admits a persistent mutation only when the authoritative operation is
prepared before genuine operator verification, revalidated inside its
committing boundary, and completed without exporting verification as a bearer.
The generic installer cannot satisfy that contract for every host and install
shape at once. Codex also caches plugin registration separately from the
Agency-owned marketplace tree, so replacing files alone neither proves the
registered plugin changed nor proves Codex loaded the replacement.

The first Codex-positive slice is therefore a repair and refresh transaction,
not a fresh bootstrap mechanism. It starts from an existing Agency marketplace
and an Agency plugin that Codex reports as installed, registered, and enabled.
Missing-host, missing-marketplace, absent-plugin, disabled-plugin, and ambiguous
inventory states do not have an authoritative prior state to restore and remain
fail-closed.

## Decision

Admit exact existing-Codex refresh on supported Windows 11 x64 hosts through one
prepared transaction. Before operator verification, capture and bind:

- the exact configuration path and security-relevant configuration revision;
- the database path and file identity, roster generation, Codex host-control
  generation, and master runtime-control snapshot and generation;
- the managed target path and parent identity, current install identity,
  plugin version, bundle digest, and complete managed-tree digest;
- the candidate component bytes and immutable launcher-publication plan;
- the exact Codex executable argv, persistent file identity and digest,
  least-privilege environment, and reported version; and
- Codex's exact Agency marketplace and plugin inventory, including enabled
  state, version, source paths, install policy, and authorization policy.

Pass that immutable primitive binding to the pinned native verifier. Its owned
window displays the existing target, current and candidate plugin versions,
current bundle digest, candidate transaction-plan digest, Codex executable
digest, configuration revision, roster generation, planned backup and
re-registration, and recovery consequence. The verifier invokes Windows Hello
through the app-owned window. It accepts only the exact nonce- and
binding-correlated result in the same call stack; it returns no receipt and no
exportable authorization capability. A same-version candidate is valid because
the operation can repair drift without changing the package version.

After verification, acquire the Agency-owned Codex install lock and prepare the
entire transaction again. Any binding difference aborts before mutation. Publish
the content-addressed private launcher runtime, revalidate its exact artifacts,
atomically replace the managed marketplace tree while retaining an exact private
backup, and attest the published bundle. Recheck Codex native inventory, remove
only `agency-preflight@agency-runtime`, prove its absence, add the same selector,
and require exact target, launcher, marketplace, plugin version, enabled state,
source, install-policy, and authorization-policy postconditions before success.

If a post-publication step fails, compensate only while the candidate, backup,
and native state still match the transaction's frozen identities. Remove a
proven candidate registration when necessary, restore the exact prior managed
tree, restore the prior plugin registration, and claim compensation only when
the complete prior target and native inventory are equal to their prepared
state. Ambiguity, drift, or incomplete restoration retains recovery evidence
and reports manual recovery required instead of overstating rollback.

This decision does not admit a fresh missing-host or missing-plugin bootstrap.
It also does not treat registration success as activation. Activation requires
restarting Codex or opening a new Codex task and then passing a capability- and
installation-bound Agency canary. Until that evidence exists, the truthful
maturity remains enabled but runtime-unverified.

## Consequences

- One exact existing Codex integration can be repaired without giving the
  generic installer broad operator authority.
- Operator approval is bound to a human-readable transaction plan, while every
  mutation and recovery claim is checked against exact machine identities.
- Same-version refresh is supported because content and registration state,
  rather than a version inequality, determine whether repair is needed.
- Missing or ambiguous prior state remains unavailable; a separate decision is
  required before fresh Codex bootstrap can become positive.
- Successful publication and registration still require restart/new-task and
  canary evidence before any loaded or production-ready claim.
- The deterministic native helper remains an unsigned review artifact.
  Authenticode publisher approval, signed-delivery mapping, and authorized legal
  disposition remain blocked under ADR-0099 and AR-161.

## Alternatives

- **Authorize the generic installer.** Rejected because its broad host and
  lifecycle surface is not one exact prepared mutation with bounded recovery.
- **Bootstrap a missing Codex integration in the same transaction.** Rejected
  because there is no exact installed target or native registration to bind and
  restore.
- **Treat a successful add command as activation.** Rejected because Codex can
  require restart or a new task before loading the replacement.
- **Return a reusable Windows Hello receipt.** Rejected because it would turn
  non-exporting same-call co-authorization into transferable authority.
