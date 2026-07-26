---
title: "Require genuine operator presence for persistent controls"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [security, dashboard, browser, controls, user-presence]
related:
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
  - docs/THREAT_MODEL.md
  - agency_runtime/server/dashboard.py
supersedes:
  - docs/decisions/0090-model-facing-control-paths-are-read-only.md
superseded_by: null
id: ADR-0096
type: decision
deciders: [maintainers]
---

# ADR-0096: Require genuine operator presence for persistent controls

## Context

ADR-0090 correctly removed mutation authority from MCP, generated hooks, and
restricted broker capabilities, but retained owner-dashboard mutations as a
human-facing exception. That assumption is false when the host exposes a
model-callable Browser that can click and type in an existing authenticated
session. The owner bearer proves local session authority; a modal phrase and
CAS prove request shape and freshness. None proves human presence.

## Decision

No persistent control or governance mutation may execute solely under
model-callable authority. The dashboard is read-only for both owner and broker
bearers until a separate OS-backed operator-presence mechanism exists. A CLI or
host-native entry point may become positive only with independent native human
co-authorization; otherwise it must fail closed rather than infer operator
intent from process ownership, a TTY, an environment variable, or a public
confirmation phrase.

A positive mutation must first prepare and seal its exact authoritative method,
resolved resource identity, payload binding, and every applicable revision or
compare-and-swap token. The trusted native prompt must show a bounded,
human-readable action, exact target, current-to-target transition, and material
consequence rather than asking a person to authorize only an opaque digest.
Deferred stdin or interactive input is part of preparation, not read after
verification. Secret-bearing payloads are bound internally with one-time
randomization and are never exposed through a stable secret-dependent digest
or plaintext prompt.
It may then request native user verification outside model authority, revalidate
the sealed state inside the committing transaction, and commit through the same
Store exactly once. A direct verification result is consumed synchronously in
that call stack and must not become an exported bearer. If a later architecture
introduces a transferable capability, that capability must additionally bind
an audience and expiry and be consumed with atomic replay protection.
Monitoring, routing, and bounded diagnostics remain available.

## Consequences

- Authenticated browser automation cannot become persistent operator authority.
- Dashboard control buttons and mutation endpoints are disabled until genuine
  presence is implemented; normal monitoring remains available.
- Existing owner-only files and OS-account trust remain filesystem boundaries,
  not proof that an Agency command was intentionally invoked by a human.
- Parsing CLI arguments before verification is not sufficient authority: the
  committing layer must bind and revalidate the resolved resource state.
- ADR-0090's read-only model-facing rule remains, but its owner-dashboard
  mutation exception is superseded.

## Alternatives

- **Keep typed modal confirmations.** Rejected because the model can read and
  type the same phrase.
- **Trust the owner bearer as presence.** Rejected because it is automatically
  attached inside the model-controlled browser.
- **Use TTY or environment detection.** Rejected because those signals are
  forgeable process context rather than native user verification.
