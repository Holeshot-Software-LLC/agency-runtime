---
title: "Use the Codex stable multi-agent feature"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, multi-agent, canary, product]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/evals/product_host.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_host_canary.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0140
type: decision
deciders: [maintainers]
---

# ADR-0140: Use the Codex stable multi-agent feature

## Context

Fresh native control `ar223-native-writer-self-contained-01` explicitly asks a
Codex parent to spawn one child carrying a self-contained writer task. The
backend completes under autonomous trust bypass but records zero spawns, zero
follow-ups, one wait, and no sentinel. That control forces the internal
`multi_agent_v2` feature.

Installed Codex CLI 0.146.0 reports `multi_agent` as stable and enabled while
`multi_agent_v2` is disabled by default. The current public Codex manual
documents `features.multi_agent` and `agents.enabled`; it does not document
`multi_agent_v2` as a supported product contract. The manual also says a direct
delegation request should spawn and that a child inherits the parent sandbox.

A direct Codex app child probe then creates and reads back exact 29-byte file
`.ar223-direct-native-child` under the fresh
`ar223-direct-native-child-01` workspace. Its bytes are exactly
`AR223_DIRECT_NATIVE_CHILD_OK` plus one LF, with SHA-256
`15afa0a7dfc371b1982dae6c0dcb50d5f9146c8ef296a9dd0e68bf1770a0148c`.
Child workspace-write capability is therefore proven independently of the
failed harness parent.

## Decision

1. Codex activation and product backends explicitly enable the supported
   stable `multi_agent` feature. They no longer force `multi_agent_v2`.
2. `agents.enabled=true` remains explicit for Agency-enabled runs. Native-only
   canaries continue disabling agents and do not enable a multi-agent feature.
3. Existing native task names, accepted inference plan authority, exact spawn
   and execution messages, one-use Store claims, waits, ciphertext correlation,
   and parent-`Stop` reconciliation remain unchanged.
4. Tests fail if either backend restores `multi_agent_v2`, omits stable
   `multi_agent`, or disables agents. Decision conformance mutates the stable
   feature back to V2 and requires the product-host contract test to kill it.
5. This local configuration repair is not live Agency proof. One new retained
   stable-surface writer sentinel must pass before the named local gate, build,
   activation, or product trial.

## Consequences

- Agency uses the current documented Codex delegation surface instead of an
  internal variant whose default and behavior can drift across CLI updates.
- The change affects host execution only; inference remains the sole staffing
  authority and no deterministic specialist selection is introduced.
- Direct child proof closes the workspace and sandbox question. The remaining
  live question is whether the stable-surface harness parent launches the exact
  child and preserves its evidence.
- Thirty-eight focused host, product, and decision tests pass with targeted
  Ruff lint and format checks.

## Alternatives

- **Continue forcing `multi_agent_v2`.** Rejected because current Codex exposes
  stable `multi_agent` as the supported default and the exact V2 control skips
  the requested spawn.
- **Treat the direct child proof as full product proof.** Rejected because it
  proves native child capability, not Agency inference, plan dispatch, header,
  or product artifacts.
- **Change inference or specialist selection.** Rejected because the failure
  occurs after staffing and before child launch.
- **Let the parent create the sentinel.** Rejected because that would conceal
  the exact delegation boundary the product must prove.
