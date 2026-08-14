---
title: "Collect child-canary proof inside disposable host profiles"
status: accepted
category: decisions
created: 2026-08-12
updated: 2026-08-12
tags: [hosts, canary, evidence, native-child, security]
related:
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/THREAT_MODEL.md
  - SECURITY.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0158
type: decision
deciders: [lkrammes]
---

# ADR-0158: Collect child-canary proof inside disposable host profiles

## Context

ADR-0036 required a no-tools, nonpersistent Claude print canary. That contract
can prove isolated plugin execution, but it cannot prove Rule 4: a native host
must start a child and its own artifact must show the exact inference-selected
cards before the child speaks. Deleting the isolated host home immediately
after the process exits also deletes the only independent origin artifact
before Agency can inspect it.

Enabling arbitrary tools or reading a caller-selected persistent profile would
weaken the canary instead of adding evidence. A Store route, specialist-load
row, backend result mapping, or caller-supplied transcript likewise cannot
establish host authorship.

## Decision

For an isolated child-delivery canary, enable only the host's native child
boundary and continue disabling unrelated tools, MCP mutation, shell, web, and
ambient configuration. Claude may persist its session only inside the
owner-private disposable `CLAUDE_CONFIG_DIR`; the complete directory is removed
after evidence collection.

The safe backend allocates an opaque live private-directory lease. The
collector accepts that lease rather than a path, derives the artifact namespace
inside it, captures the namespace identity and an empty bounded scan, and then
brackets the real host process with a one-use invocation window. Collection
runs while the same isolated home and lease are alive. A green transition
requires exactly one new canonical host artifact whose filesystem timestamp and
host event fall inside that invocation window, plus exact parent, child, route,
card, decision, install, and pre-speech bindings and the Store's atomic one-use
receipt. The collector returns a sealed in-process capability separately from
ordinary result and Store mappings. Canary evaluation consumes that capability
once.

Caller-selected roots remain diagnostic and read-only. No CLI or dashboard
operation may mint a delivery receipt, and Store-only state cannot create the
capability. Missing, ambiguous, stale, replayed, noncanonical, or unsupported
artifacts fail the canary open as unstaffed. Codex card delivery through the
current opaque channel remains unsupported; Codex remains a supported host and
proceeds unstaffed.

This decision narrows ADR-0036's no-tools and nonpersistent clauses only for a
bounded Rule-4 child-delivery measurement. ADR-0036's confirmation, isolation,
least-privilege, correlation, attestation, and invalidation requirements remain
in force.

## Consequences

- A Claude canary can measure native child delivery without touching the real
  profile or retaining child content after the invocation.
- The canary necessarily permits one native child tool and may make more than
  one model request, but no unrelated tool capability is enabled.
- Store projections and host artifacts remain separately attributable: neither
  can certify delivery alone.
- A host without an attributable pre-speech artifact remains supported but
  unproven and unstaffed for Rule 4.
- Same-process private reflection and same-account transcript plus Store
  forgery remain outside the sandbox boundary documented by the threat model;
  this lease is invocation scoping, not protection from code already executing
  as the owner inside the Agency process.

## Alternatives

- **Keep the no-tools canary.** Rejected because it cannot exercise or prove a
  native child boundary.
- **Inspect the user's persistent host profile after execution.** Rejected
  because ambient history and caller-controlled roots do not establish this
  invocation's origin and would expose unrelated content.
- **Accept Store or backend mappings as proof.** Rejected because Agency would
  attest to its own output.
- **Retain the isolated profile for later inspection.** Rejected because the
  proof can be collected in-lifetime and the profile contains authentication
  material and host transcripts.

## Provenance

AR-255 runtime `7e1b3603` and ledger `fb650b04` record the source checkpoint
and adversarial verification. AR-180 owns exact-install and live host proof;
simulation does not upgrade installed or live matrix layers.
