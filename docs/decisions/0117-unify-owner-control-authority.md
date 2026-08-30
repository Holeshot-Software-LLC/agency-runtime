---
title: "Unify owner CLI and dashboard control authority"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [security, dashboard, cli, controls, installation, automation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
  - docs/THREAT_MODEL.md
  - README.md
supersedes:
  - docs/decisions/0111-install-the-applicable-suite-by-default.md
superseded_by: null
id: ADR-0117
type: decision
deciders: [maintainers]
---

# ADR-0117: Unify owner CLI and dashboard control authority

## Context

ADR-0096 introduced an Agency-owned human-presence requirement because a model-
callable browser can exercise an owner dashboard session. ADR-0110 then removed
the verifier but retained fail-closed owner mutations. ADR-0111 restored the
dashboard to the default installation suite without restoring its configuration
authority. Production therefore installs a dashboard advertised with controls,
ships tested mutation handlers, and disables them; normal CLI mutations enter a
verifier that always reports unavailable.

The product also supports autonomous, owner-directed operation in disposable
containers. Once code runs as the same operating-system account and holds the
same owner credential, Agency cannot reliably distinguish a person from that
person's delegated agent. Pretending otherwise blocks supported automation
without creating a real security boundary.

## Decision

Treat a normal owner CLI invocation and the owner dashboard bearer as equivalent
local owner authority for Agency configuration, runtime, roster, workforce,
maintenance, and owned-service controls. Both human operators and autonomous
agents may exercise that authority. Agency does not require a second OS human-
presence ceremony.

Keep model-facing hook, MCP, and broker credentials read-only. They never
receive the owner dashboard bearer. If an owner deliberately gives a model the
normal CLI environment or opens an owner dashboard session in a model-
controlled browser, that is delegation of owner authority, not evidence of
human presence.

Preserve exact confirmation phrases, expected revisions and generations,
ownership checks, immutable preparation, dry runs, bounded compensation, and
postconditions wherever the underlying operation requires them. These controls
prevent accidents, stale writes, and partial claims; they do not authenticate a
human.

The dashboard remains an optional component selected by bare `agency install`
on supported hosts. `--no-dashboard` opts out. `agency dashboard service open`
is an owner convenience operation: it may install, repair, start, or restart an
Agency-owned service before opening the automatically authenticated loopback
URL. It must preserve ownership checks and must not disclose the bearer in
terminal output.

The dashboard's per-launch bearer remains automatic request isolation, not a
login or presence ceremony. Loopback binding, strict Host and Origin checks,
credential separation, and token scrubbing remain required because unrelated
browser content and local processes are not implicitly owner dashboard clients.

## Consequences

- Dashboard and CLI controls can implement the product story instead of
  returning a permanent unavailable-verifier error.
- Human and autonomous owner workflows use the same transactional safety
  contract and produce the same evidence.
- A process with the owner's OS account and credential can mutate Agency state;
  that authority is explicit in the threat model rather than disguised as a
  solvable presence distinction.
- Broker, hook, and MCP compromise still does not confer persistent mutation
  authority unless the owner separately delegates owner credentials or CLI
  execution.
- The dashboard is optional in capability but included by default in product
  installation.

## Alternatives

- **Rebuild Agency-owned Windows Hello.** Rejected because it blocks autonomous
  operation, duplicates host trust, and cannot authorize a multi-resource
  application transaction coherently.
- **Keep the dashboard read-only.** Rejected because it contradicts the
  advertised configuration/control surface and duplicates CLI without its
  primary function.
- **Remove dashboard authentication.** Rejected because loopback alone does not
  prevent cross-site browser requests or unauthorized local clients.
- **Treat every same-account agent as untrusted while allowing the same CLI to
  mutate.** Rejected because there is no enforceable distinction at that
  boundary.

