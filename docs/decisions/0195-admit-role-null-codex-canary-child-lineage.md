---
title: "Admit role-null Codex canary child lineage under the ciphertext anchor"
status: accepted
category: decisions
created: 2026-08-31
updated: 2026-08-31
tags: [codex, canary, lineage, windows, host-integrations]
related:
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/decisions/0194-admit-host-encrypted-codex-canary-task-delivery.md
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/handoffs/issue-AR-338.md
supersedes: []
superseded_by: null
id: ADR-0195
type: decision
deciders: [maintainers, owner]
---

# ADR-0195: Admit role-null Codex canary child lineage under the ciphertext anchor

## Context

The AR-338 Windows bring-up measured, on codex-cli 0.150.1 and again on the
exactly-proven 0.151.0, that this machine's Codex exposes the `spawn_agent`
collaboration tool without the `agent_type` parameter: a live schema probe
returns `fork_turns, message, model, reasoning_effort, task_name`. The
account on the Linux GO machine exposes `agent_type` on the identical binary
and an equivalent configuration, so the exposure is a server-side,
account-scoped rollout gate — not a config, platform-build, or version
difference. The activation canary's parent is instructed to pass the plan
row's `native_agent_type` as `agent_type`; on a gated account the model
cannot comply, every child is born with the exact role-less 0.149.1 metadata
shape under a newer version string (`agent_role` absent from the session
payload, `thread_spawn.agent_role` null), and two fail-closed artifact
contracts reject it: the 0.150.1/forward child lineage parser requires
`agent_role == "Code Reviewer"` on both sides, and the child rollout shape
gate admits only the three-key legacy spawn when the parent's attested call
was role-less. The join then declines, the child is honestly left unstaffed,
and `verify-activation` can never mint an attestation on such an account.

The spawn-call recognizers already admit the role-less call itself (the
0.149 legacy shape), and ADR-0194's host-encrypted delivery proof — byte
equality between the parent's attested spawn ciphertext and the sole
pre-speech `NEW_TASK` envelope the child received — was verified present in
the rejected artifacts.

## Decision

Admit one named metadata-less variant of the Codex canary child lineage,
consistently on both artifact contracts:

1. The child lineage parser admits, for 0.150.1 and ADR-0193 forward
   versions, a session payload with the exact role-less 0.149.1 key set
   (never a present-but-null top-level `agent_role`; forward versions keep
   the same bounded additive unknown-key tolerance), and then requires the
   nested `thread_spawn.agent_role` to be null. A role on either side alone
   still fails closed.
2. The child rollout shape gate admits the modern five-key spawn source
   with a null `agent_role` and a valid nickname when and only when the
   parent's attested spawn call carried no `agent_type`.

Every other invariant is unchanged: exact metadata keys, `codex_exec`
originator, thread lineage and depth, UUIDv7 timing bounds, cwd equality,
the one-use Store verification consumer, and ADR-0194's ciphertext
byte-equality anchor, which carries the actual delivery proof.

## Consequences

`verify-activation` and the restricted canary can pass on accounts where
the host offers no way to type the spawned agent, and the proof they mint
rests on the same anchors as ADR-0194. The role equality remains enforced
wherever the host exposes `agent_type`, so an account with the richer
schema cannot silently drop the typed spawn. A forged or mixed artifact —
role on one side only, a stringly role under a role-less spawn, or a
present-but-null top-level role — still fails closed. When the upstream
rollout reaches gated accounts, their children regain the explicit role and
the stricter branch applies automatically.

## Alternatives

Waiting for the upstream account rollout leaves the Windows harness set
unverifiable for an unknown period. Relaxing the role check universally
(ignoring `agent_type` everywhere) would erase the typed-spawn binding on
accounts that do expose it. Teaching the instruction layer to force a role
through the task message would put contract-bearing content inside the
model-authored prompt, which the canary deliberately forbids.
