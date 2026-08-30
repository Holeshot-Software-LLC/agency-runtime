---
title: "Bind live host canary attestations to capability and installation identity"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-20
tags: [hosts, canary, evidence, installation, security]
related:
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-67-require-explicit-native-enablement-proof.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0036
type: decision
deciders: []
---

# ADR-0036: Bind live host canary attestations to capability and installation identity

## Context

Generated files, synthetic hooks, and successful registration commands do not
prove that a native host loaded an integration and produced correlated routing
and finalization evidence. Conversely, one historical canary must not remain
current after a host upgrade, plugin reinstall, or managed-bundle change.

Agent hosts have different safe noninteractive capabilities and evidence
surfaces. Some expose model receipts while others do not. A generic canary that
requires every signal would be impossible for some hosts; one that accepts any
new database row could falsely attest unrelated concurrent activity.

## Decision

Provide an explicit, exact-confirmed live-canary command. Readiness and planning
are nonmutating. Execution is available only for a host with a proven
noninteractive, no-tools safety contract; unsupported hosts fail closed rather
than inheriting another host's argv.

Give each canary prompt a random nonce and require the exact prompt hash in a
new routing decision. Require routing and finalization events to share a trace
for the target host. Require a model receipt only for hosts whose integration
contract exposes authoritative response telemetry. Process success and a valid
final response header are necessary but are not evidence substitutes.

Persist only a bounded attestation after every required signal succeeds. Bind
it to platform identity, host version, plugin version, install UUID, managed
bundle digest, trace, timestamp, and profile scope. An upgrade, reinstall,
bundle change, native-state mismatch, or scope mismatch makes the attestation
stale. An isolated-profile canary proves that temporary installation and host
invocation worked; it never promotes the user's current profile to registered,
enabled, loaded, or canary-verified.

For Codex, copy only the bounded authentication artifact into an owner-private
temporary `CODEX_HOME`, register the local managed marketplace and plugin
there, verify temporary inventory, use an empty working directory and read-only
sandbox, disable shell, web, apps, and unrelated MCP mutation, and delete the
profile afterward. Claude uses its documented safe, no-tools, nonpersistent
print contract. Host auth material, prompts, and responses are not stored in
the attestation.

## Consequences

- Support output can distinguish deterministic contract coverage, isolated
  live compatibility, and the current profile's native state.
- Concurrent unrelated runtime activity cannot satisfy a canary.
- Successful evidence automatically expires when relevant installation or host
  identity changes.
- Live canaries may make a billable model request and therefore remain an
  explicit operator action.
- Hosts without a proven safe automation surface remain below live-canary
  maturity even when their generated bundle is contract-tested.

## Alternatives

- Treat successful installer exit as a canary. Rejected because registration
  and loading are separate host facts.
- Accept any post-invocation evidence delta. Rejected because concurrent work
  could produce a false positive.
- Store one permanent boolean per host. Rejected because upgrades and
  reinstalls invalidate the result.
- Require a model receipt from every host. Rejected because receipt capability
  is host-specific and must not be synthesized.
- Run against the real user profile by default. Rejected because a verification
  command must not silently rewrite active agent configuration.

## Provenance

AR-03, AR-04, and AR-07 record the implementation, live evidence, and release
gate. The implementation commit is linked after final validation.
