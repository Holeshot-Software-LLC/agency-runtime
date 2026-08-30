---
title: "Admit host-encrypted Codex canary task delivery"
status: accepted
category: decisions
created: 2026-08-30
updated: 2026-08-30
tags: [host-integrations, codex, canary, delivery, security-posture]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/roadmap/issue-AR-334-support-codex-0151-collaboration-and-hook-contract.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/canary_backends.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0194
type: decision
deciders: [maintainers, owner]
---

# ADR-0194: Admit host-encrypted Codex canary task delivery

## Context

The restricted Codex activation canary proved child delivery at
`SubagentStart` (ADR-0179): the hook staffed the fixed code-reviewer unit
against the real child UUID and injected the v6 team envelope, and the child
rollout later carried that envelope in plaintext for the delivery verifier
(ADR-0156). codex-cli 0.151 removed both preconditions in exec mode, verified
live on 2026-08-30 against real rollouts: the host no longer emits
`SubagentStart` at all (`SubagentStop` still fires), and the inter-agent
channel is host-encrypted end to end — the parent's `spawn_agent` call records
an opaque token as its `message` while the hook observes the decrypted
plaintext, and the child rollout receives the same token inside a
`Message Type: NEW_TASK` input envelope. No hook can inject a card into the
child, and no plaintext envelope can appear in either artifact. The one
compensating observation: the ciphertext recorded by the parent's attested
spawn call is byte-identical to the ciphertext the child received.

## Decision

For admitted release-shaped Codex versions whose collaboration channel is
host-encrypted (ADR-0193 dispatch, 0.151 and newer):

1. The restricted canary spawn is recognized at `PreToolUse` in both observed
   forms — the 0.150 opaque message and the 0.151 hook-decrypted plaintext
   that exactly equals the fixed canary work unit — and, inside the proven
   restricted parent scope, it is left to the restricted flow instead of
   ordinary plaintext staffing. The hook stays non-blocking and writes
   nothing at that boundary.
2. The child-bound canary staffing decision moves to the first hook that
   still carries the real child UUID: the `SubagentStop` join (artifact-
   anchored through the ADR-0193 parser). Staffing, promotion of the pending
   synthetic dispatch, and delivery collection run there.
3. Child delivery verification admits a host-encrypted grade: the child
   artifact must carry exactly one pre-speech `NEW_TASK` envelope whose
   ciphertext byte-equals the `message` of the sole attested parent spawn
   call, with exact lineage (`session_meta` thread spawn), role, task-name,
   and timing invariants, bound to the Store decision through the same
   one-use atomic verification consumer as the v6 path. The verification
   reason names the grade; the v6 plaintext path remains preferred and
   unchanged wherever the host still exposes it.

What this grade attests is the task payload round trip: the child provably
received, byte for byte, the payload of the parent's attested canary spawn,
under a proven canary parent route whose query digest pins the plaintext
task. What it does not attest — stated deliberately — is transport of the
specialist card capsule into the child: the host's encrypted channel carries
only the parent-authored task, so `cards` on the verified proof reflect the
Store-staffed team, not bytes observed inside the child artifact.

## Consequences

The restricted canary and `verify-activation` pass again on hosts that
encrypt inter-agent channels, without weakening any 0.149/0.150 contract:
every existing plaintext invariant still verifies byte-exactly where it is
observable, ordinary (non-canary) spawns keep the ordinary staffing path, and
a canary-shaped spawn outside the proven restricted scope changes nothing.
The delivery proof for host-encrypted channels is explicitly labeled, so
downstream consumers can distinguish it from v6 plaintext proof. If a future
Codex release re-exposes a hook injection point or a plaintext envelope, the
stricter proof re-engages without a further decision.
