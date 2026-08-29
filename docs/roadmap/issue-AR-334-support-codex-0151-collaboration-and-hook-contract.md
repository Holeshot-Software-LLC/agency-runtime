---
title: "AR-334: Support Codex 0.151 collaboration and hook contract"
status: open
category: roadmap
created: 2026-08-29
updated: 2026-08-29
tags: [bug, host-integrations, codex, canary, collaboration, rollout]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
  - docs/roadmap/issue-AR-333-report-unsupported-codex-isolated-agency-canary.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-334
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/349
depends_on: []
blocks: []
---

# AR-334: Support Codex 0.151 collaboration and hook contract

## Problem

codex-cli auto-updated from 0.150.1 to 0.151.0 and the AR-330 live contracts
no longer hold. The current-profile activation canary fails with
`codex_collaboration_projection_unavailable` even though attended trust
succeeded, the parent spawns exactly one child, and the child completes.

## Current state

- Verified drift points from the real 2026-08-29 rollouts: the child rollout
  no longer carries the decrypted Agency prompt-delivery envelope in
  plaintext (the spawn task arrives as a `Message Type: NEW_TASK` turn with
  an `encrypted_content` item plus a new top-level
  `inter_agent_communication_metadata` row), so
  `_codex_child_prompt_delivery` finds zero deliveries; canary stdout
  session-id extraction returns None; and new rollout shapes (`world_state`,
  `item_completed`, `token_count`, message items carrying
  `internal_chat_message_metadata_passthrough`) surround the 0.150-era
  allowlists. `multi_agent_version` remains `v2` on both sides.
- An in-session replay of the installed projection pipeline against the real
  0.151 rollouts passes parent parsing, direct-call extraction, child loading,
  and the tool-free assertion, then raises "Codex child rollout did not carry
  one exact prompt delivery".
- `agency install --agent codex --verify-activation` exits 1 with this cause;
  receipts are retained under
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/`.
- Attended trust itself succeeded and is not implicated; zero model calls
  were wasted on the deterministic refusals.


- Implemented and merged as `ec46aced` (PR #352) with seven forward-version
  tests; the branch parser resolves the retained real 0.151.0 child rollout
  to its exact parent. Live verify-activation and the restricted canary wait
  on the operator's fresh attended trust after the `6606ebed` install rotated
  the launcher digest.

## Approach

The owner directed on 2026-08-29 that nothing on the host system is pinned
and the code accounts for new versions; ADR-0193 records the admitted
mechanism. The 0.151.0 child metadata proved byte-compatible with the 0.150.1
contract except for the version string, so the version dispatch now admits
release-shaped newer versions under the newest proven contract with bounded
additive tolerance and exact structural invariants.

Characterize the 0.151 delivery routing (where the decrypted spawn message
is now observable, if anywhere), extend the rollout and stdout projections to
the 0.151 vocabulary behind exact version-scoped fixtures captured from real
rollouts, and keep every existing 0.150 contract intact. If 0.151 makes the
plaintext delivery envelope structurally unobservable in host artifacts,
bring the alternative proof (Store-side delivery receipts at SubagentStart)
through a decision record before relaxing ADR-0156 expectations.

## Dependencies

AR-333 (readiness must not report ready for refusing combinations). An owner
decision on pinning codex 0.150.1 versus carrying this support is the
short-term unblock for AR-297's Codex gates.

## Acceptance

- [ ] Current-profile activation canary passes on codex-cli 0.151 with
      verified child delivery evidence.
- [ ] Version-scoped fixtures from real 0.151 rollouts cover parent and child
      projections.
- [ ] `agency install --agent codex --verify-activation` exits 0 with a fresh
      persisted attestation on 0.151.
- [ ] 0.150 contracts remain green.
