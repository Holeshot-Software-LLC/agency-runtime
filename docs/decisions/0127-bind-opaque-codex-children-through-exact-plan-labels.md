---
title: "Bind opaque Codex children through exact plan labels"
status: superseded
category: decisions
created: 2026-07-31
updated: 2026-07-31
tags: [codex, delegation, activation, security, privacy, evidence]
related:
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
id: ADR-0127
type: decision
deciders: [maintainers]
---

# ADR-0127: Bind opaque Codex children through exact plan labels

## Context

The fixed Codex activation canary passed while an ordinary inferred product
team could not start its first child. Retained host evidence and hook code
identify the discrepancy: Codex presents the collaboration message to
`PreToolUse` as opaque ciphertext, but the hook required the message to hash to
the persisted plaintext goal. Only the fixed package-owned canary could
recover a known plaintext constant.

The Codex `SubagentStart` contract exposes parent session and turn correlation,
child identity, model, workspace, and transcript path, but not the decrypted
native assignment. Rewriting the opaque input is also invalid: the host owns
decryption, and combining a replacement with its encrypted block causes child
launch failure. A general product contract therefore cannot reproduce the
canary's closed-world plaintext recovery.

## Decision

Keep exact plaintext goal equality for every host input that exposes
plaintext. Add one Codex-specific opaque path with these boundaries:

1. The message must match Codex's bounded encrypted collaboration-message
   shape. The unencrypted native task label must resolve exactly one work-unit
   row in the ready isolated plan for the correlated session and trace. An
   absent, unpersisted, or ambiguous label does not authorize a specialist.
2. `PreToolUse` leaves the ciphertext byte-for-byte unchanged. It issues one
   native-hook grant only for the resolved row's immutable specialist,
   work-unit ID, goal hash, mutation scope, and evidence requirements.
3. External-write rows remain forbidden. Read-only rows receive no mutation
   paths. Workspace-write rows receive only `.` inside the product host's
   already isolated workspace because content-free resource hashes cannot be
   reversed safely into path strings.
4. `SubagentStart` records the host child identity, retrieves exactly one
   unconsumed matching grant, re-resolves the persisted plan row, and injects a
   v2 context. The context contains the immutable specialist prompt and
   content-free goal hash, but no plaintext task or bearer token. The grant is
   consumed against that observed child before the child proceeds.
5. Product evidence reads the v2 goal hash directly. It never derives a false
   hash from an empty placeholder and never retains the native task,
   ciphertext, specialist prompt, child tool inputs or outputs, or final child
   message.

The source-controlled product developer instruction still requires the parent
to send each row's exact decoded goal. Current Codex does not expose that
plaintext or a host-authenticated digest to either relevant hook, so Agency
cannot independently prove semantic message equality before child execution.
The exact persisted label, host-preserved ciphertext, one-use grant, isolated
workspace, and child lifecycle are the strongest observable binding on this
host. If Codex exposes a decrypted-task digest or equivalent attestation,
Agency must tighten this contract to verify it.

## Consequences

- The activation canary and ordinary product delegation now exercise the same
  arbitrary-goal launch boundary instead of a canary-only exception.
- The parent still cannot select or broaden a specialist: its task label maps
  to one inference-authored persisted row, and every other identity is
  rejected.
- Codex child input remains decryptable by Codex because Agency no longer
  rewrites an opaque block.
- Workspace-write authority is coarser than a plaintext file-specific grant,
  but remains bounded by the exact isolated product workspace and cannot
  become external write.
- Evidence proves the selected row, goal hash, specialist version, child
  identity, grant consumption, and lifecycle without storing private content.
- The current host opacity limitation is explicit rather than hidden behind a
  passing fixed canary.

## Alternatives

- **Keep canary-only recovery.** Rejected because it proves a fixed constant
  while making every arbitrary Codex specialist launch impossible.
- **Accept any opaque child without a persisted label.** Rejected because it
  would let the parent invent specialist identity and bypass inference-owned
  staffing.
- **Rewrite the encrypted input with a v1 envelope.** Rejected because Codex
  owns decryption and the combined payload fails before child start.
- **Persist plaintext goals for later hook recovery.** Rejected for this
  package because it expands durable content retention and schema scope when a
  content-free exact-row binding is sufficient for the isolated product host.
- **Derive resource paths from stored hashes.** Rejected because hashes are not
  reversible; pretending otherwise would create fictional least-privilege
  evidence.
