---
title: "Separate native trust modes from activation proof"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [host-integrations, trust, activation, automation, canary, codex]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - README.md
supersedes:
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
superseded_by: null
id: ADR-0119
type: decision
deciders: [maintainers]
---

# ADR-0119: Separate native trust modes from activation proof

## Context

Codex native hooks normally require host-managed trust. ADR-0077 correctly
separated registration from behavioral activation but allowed only attended
current-profile readiness. Agency also targets autonomous builders that create
fresh containers, install a harness and Agency, and dispatch work without a
human available to approve hook hashes.

Tests currently prove backend environment construction and hook behavior in
separate processes, while a real Codex run has shown that those facts do not by
themselves prove hook start, route persistence, exact specialist injection, or
delegation.

## Decision

Expose two explicit native trust modes:

1. **Attended mode** uses the harness's normal trust lifecycle. Agency may
   inspect and report native trust but never writes undocumented host trust
   state.
2. **Autonomous mode** is explicitly requested for an owner-controlled isolated
   or disposable environment. It may use a harness-supported noninteractive
   trust bypass for the exact Agency invocation. Evidence records
   `trust_mode=autonomous_bypass` and never reports the hooks as trusted.

Both modes require the same behavioral activation proof before Agency reports
runtime readiness. Registration, enablement, trust mode, hook start, route,
inference decision, exact specialist injection, native spawn, native child
completion, and finalization are separate evidence stages. No earlier stage
implies a later one.

The shared product test backbone validates installation payloads, invocation
contracts, evidence schemas, failure semantics, and one-use specialist identity
independently of the host. Each supported harness adapter then owns a bounded
live canary that proves its real process carries the exact contract into hooks
and children. Synthetic halves cannot substitute for that adapter canary.

Autonomous mode does not weaken filesystem, executable, plugin ownership,
sandbox, workspace, tool, output, timeout, or evidence-correlation checks. It
does not grant persistent dashboard, MCP, hook, or broker mutation authority.

## Consequences

- Fresh container builders can install and prove Agency without an impossible
  interactive trust step.
- Existing user profiles retain native host trust by default and are never
  silently rewritten or mislabeled.
- A trusted hook inventory is useful preflight evidence but is not activation.
- Host-specific failures become visible at one named stage instead of being
  summarized as generic installation failure.

## Alternatives

- **Require attended trust everywhere.** Rejected because it makes autonomous
  container installation impossible.
- **Silently bypass trust whenever no TTY exists.** Rejected because it hides an
  authority change and can surprise existing profiles.
- **Treat registration or a trusted inventory as activation.** Rejected because
  neither proves a routed prompt or specialist lifecycle.
- **Rely only on synthetic adapter tests.** Rejected because the real host owns
  environment propagation, hook scheduling, and native child behavior.

