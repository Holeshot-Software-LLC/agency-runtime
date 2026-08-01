---
title: "Treat product specialist loads as turn-scoped"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [product, codex, specialists, delegation, evidence, workspace]
related:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md]
superseded_by: null
id: ADR-0133
type: decision
deciders: [maintainers]
---

# ADR-0133: Treat product specialist loads as turn-scoped

## Context

The exact `f8e607d` product trial accepted eight inferred work units and ran
eight native Codex children. One immutable `code-reviewer` version served two
different review units, so the Store correctly retained seven turn-scoped
specialist-load rows alongside eight grants, consumptions, delegations, and
worker lifecycles. ADR-0124 instead required one load row per unit, which made
valid specialist reuse impossible to prove.

The same trial left its isolated workspace empty. Codex delivered each
decrypted unit goal as the native child message and injected the audited
specialist prompt separately, but the injected text described the goal only as
"separate." That wording allowed a child to treat the specialist prompt as the
request instead of executing its native message. The parent plan also omitted
the already-verified mutation mode, so the product write-proof owner was not
explicit at the scheduling boundary.

Finally, the persisted eight-spawn/eight-wait baseline passed while the exact
projector collapsed its first rejected invariant into
`native_collaboration_topology_invalid`. That preserved privacy but discarded
the bounded fact needed for a one-build repair.

## Decision

Supersede ADR-0124 while retaining its inference-owned unit graph, non-working
parent, per-unit native execution, first-pass header, zero-correction, and
artifact-validation requirements.

1. Require one specialist-load row per unique selected specialist slug, not per
   work unit. The load must be anchored to a consumed grant, and every reused
   unit grant for that slug must carry the same immutable version and prompt
   hash. Conflicting identities under one slug fail closed. Every unit still
   requires its own exact grant, consumption, delegation, worker lifecycle,
   native spawn, prompt delivery, and successful child completion.
2. Render each accepted plan row's verified mutation mode at the parent
   scheduling boundary. For product trials, the first `workspace_write` unit
   owns the prompt-bound sentinel as its first mutation; read-only children and
   the non-working parent may not create it.
3. Tell every opaque Codex child explicitly that its decrypted native message
   is the exact work-unit goal and that it must execute that goal under the
   injected specialist instructions. Workspace tools must be used when the
   goal requires implementation or documentation changes. Store-backed scope
   and the outer isolated workspace remain the authority boundaries.
4. Preserve the first exact projector rejection as an allowlisted,
   content-free invariant code. Never retain private prompts, tool arguments,
   tool outputs, or model responses in that diagnostic.

## Consequences

- Reusing one exact specialist for several units no longer invents duplicate
  load events, while every unit remains independently execution-proven.
- A specialist child receives an unambiguous goal/role relationship without
  copying plaintext goals into public evidence or durable activation metadata.
- The model-authored sentinel has one explicit specialist owner and still
  proves effective workspace-write behavior rather than an outer harness
  write.
- A future host-shape rejection identifies its first bounded invariant on the
  same build instead of forcing another diagnostic-only product trial.
- All malformed identity, lineage, topology, workspace, and correction cases
  continue to fail closed.

## Alternatives

- **Insert one duplicate load row per unit.** Rejected because a turn-scoped
  immutable specialist is loaded once; duplicate rows would fictionalize
  runtime behavior.
- **Drop specialist-load proof for reused units.** Rejected because the shared
  load must still be anchored to an exact consumed grant for the same immutable
  specialist identity.
- **Let the parent create the sentinel.** Rejected because a generalist parent
  write would not prove delegated specialist execution.
- **Persist raw validator exceptions.** Rejected because exception text can
  expose host or prompt content and is not a stable evidence contract.
