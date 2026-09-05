---
title: "Retire removed-helper release obligations without waiving artifact proof"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [release, governance, backlog, supersession]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-167-normalize-windows-release-source-modes.md
  - docs/roadmap/issue-AR-169-exclude-native-pe-from-portable-wheel.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
superseded_by: null
id: ADR-0219
type: decision
deciders: [maintainers]
---

# ADR-0219: Retire removed-helper release obligations without waiving artifact proof

## Context

The owner requested evidence-led backlog cleanup on 2026-09-05. ADR-0110 and
AR-197 already removed the Agency-owned Windows Hello helper; commit f5ca1729
removed its release payload. The present release contract sets
includes_native_executable=false for both wheel profiles. Nevertheless,
ADR-0098 still requires a PE in the Windows wheel and ADR-0099 still requires
signing that removed helper. AR-167/169 and parts of AR-160 repeat those stale
obligations. Implementing them now would reverse the accepted removal.

## Decision

Reconcile the records to the existing product, without changing runtime or
packaging code:

- Retain the current portable and Windows x64 wheel profiles, their finite
  metadata differences, canonical Git-blob construction, identical producer
  source distributions, and independently verified three-artifact release set.
- Both profiles reject executables and structurally valid PE payloads. Do not
  restore the helper, its source/provenance payload, its special executable-mode
  allowance, or its Authenticode/legal-delivery ceremony to complete old work.
- Retire AR-167 and AR-169 as wont_do with their original criteria preserved.
  This is supersession, not a claim that their historical Windows builds passed.
  General path/handle mode integrity and cross-OS artifact evidence remain in
  the current AR-160 package and existing build/verification tests.
- Keep AR-160 in progress. Preserve its old checklist as historical evidence
  and replace its active acceptance with the current no-helper release contract.
  No prior checkbox or historical artifact becomes current-candidate proof.
- ADR-0099's helper-specific unsigned-to-signed mapping is retired. Existing
  non-helper supply-chain, publication, credential and authorization controls
  remain unchanged. This decision does not approve publication or claim legal
  clearance.

## Consequences

The backlog no longer directs an agent to reintroduce removed native bytes.
Windows/Linux artifact verification is still required for a release; Linux
unit tests do not stand in for Windows producer evidence. The somewhat unusual
two-profile packaging policy remains as implemented: simplifying it is a
separate product change, not an inferred cleanup permission.

## Alternatives

- Finish the original PE delivery and signing work: conflicts with ADR-0110.
- Mark the old issues done: would claim abandoned acceptance was satisfied.
- Remove all cross-platform gates or the Windows wheel: would expand a record
  reconciliation into an unrequested packaging redesign.
- Leave both incompatible contracts active: reproduces the original problem.
