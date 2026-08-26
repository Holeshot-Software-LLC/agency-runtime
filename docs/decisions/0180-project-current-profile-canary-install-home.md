---
title: "Project current-profile canary install-home authority"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, installation, native-child, security]
related:
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_install_identity.py
  - tests/test_codex_activation_verification.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0180
type: decision
deciders: [maintainers]
---

# ADR-0180: Project current-profile canary install-home authority

## Context

ADR-0179 permits one exact Store-backed Codex canary delivery only when it is
bound to the immutable managed host installation serving the hook. The shared
identity reader treats `AGENCY_CANARY_MODE=1` as an isolated authority domain:
it refuses ambient `HOME` and requires the parent to name the original owner
home explicitly. The Claude canary already passes that capability because it
redirects `HOME`; the current-profile Codex backend did not because it retains
the owner's normal home.

The second exact AR-297 Codex retry proved the consequence. Native Codex
created and completed the fixed child, but the restricted hook reached no child
staffing decision. An installed-runtime diagnostic reproduced the boundary:
the identity is absent without the capability and exact, runtime-matched, and
current when that capability alone is present.

## Decision

Every Agency canary that can deliver native-child context must project
`AGENCY_CANARY_NATIVE_INSTALL_HOME` explicitly, including a current-profile
Codex canary whose process otherwise retains the owner home. The value comes
only from the backend's source environment through the existing source-home
resolver and is normalized to an absolute path before launch.

The identity reader remains unchanged. Canary mode never falls back to ambient
`HOME`, `USERPROFILE`, a host config directory, or a plugin path. It still
derives the host target through installer path rules and revalidates the owned
tree, install manifest, launcher artifacts, bundle identity, projected runtime,
and stable reread. This capability does not select a specialist, admit an
artifact, alter trust policy, or bypass activation.

## Consequences

The normal no-bypass current-profile Codex canary can bind its child delivery
to the same immutable installation that executed the managed relay. A missing,
relative, redirected, stale, or mismatched owner home continues to fail closed.
The value is an authority path rather than a credential and remains scoped to
the canary subprocess.

The production container must still prove the exact route, default host role,
fixed child path and unit, v6 artifact, one-use receipt, current header,
accepted finalization, and attestation. This decision supplies only the missing
install-identity input to that chain.

## Alternatives

Letting canary mode infer authority from ambient `HOME` was rejected because it
would silently weaken the isolated-host boundary. Removing canary mode from the
current-profile process was rejected because that marker gates the exact
activation contract and evidence collection. Accepting a missing install
identity was rejected because Store state and hook prose cannot replace an
immutable managed-install binding. Redirecting Codex into an isolated home was
rejected because this package specifically proves the installed current
profile and its later ordinary unattended behavior.
