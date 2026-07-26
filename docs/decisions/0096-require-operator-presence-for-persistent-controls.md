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

No Agency surface callable by a model may perform a persistent control or
governance mutation. The dashboard is read-only for both owner and broker
bearers until a separate OS-backed operator-presence mechanism exists. Model
facing CLI and host-native entry points must fail closed rather than infer
operator intent from process ownership, a TTY, an environment variable, or a
public confirmation phrase.

A future mutation capability must be short-lived and single-use, be minted only
after native user verification outside model authority, bind the exact method,
target, payload digest, observed generation, and expiry, and be consumed
atomically. Monitoring, routing, and bounded diagnostics remain available.

## Consequences

- Authenticated browser automation cannot become persistent operator authority.
- Dashboard control buttons and mutation endpoints are disabled until genuine
  presence is implemented; normal monitoring remains available.
- Existing owner-only files and OS-account trust remain filesystem boundaries,
  not proof that an Agency command was intentionally invoked by a human.
- ADR-0090's read-only model-facing rule remains, but its owner-dashboard
  mutation exception is superseded.

## Alternatives

- **Keep typed modal confirmations.** Rejected because the model can read and
  type the same phrase.
- **Trust the owner bearer as presence.** Rejected because it is automatically
  attached inside the model-controlled browser.
- **Use TTY or environment detection.** Rejected because those signals are
  forgeable process context rather than native user verification.
