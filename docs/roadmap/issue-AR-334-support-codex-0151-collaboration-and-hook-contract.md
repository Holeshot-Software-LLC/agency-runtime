---
title: "AR-334: Support Codex 0.151 collaboration and hook contract"
status: in_progress
category: roadmap
created: 2026-08-29
updated: 2026-08-30
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


- Remaining on 2026-08-29 night: the ordinary codex turn passes the full bar
  on 0.151 (staffing, finalization, header, Stop-gated publication), and the
  parser plus the parent canary snapshot are individually proven, but
  `verify-activation` still fails closed at the child-side delivery join
  (`_restricted_codex_activation_child_parent_scope` returns None while its
  observable preconditions pass post-hoc; the mid-turn open-trace state is
  not reconstructable afterwards). Next bounded step: run the restricted
  canary with `AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS=1` and, if needed, give
  the child-scope join a content-free recorded refusal reason.
- Child-join fixes landed 2026-08-30 against the two verified 0.151 hook
  drifts: the `transcript_path`/`agent_transcript_path` hints are optional
  with a fail-closed fallback to the sole child-named rollout under the
  canonical sessions root (the metadata parser stays the trust anchor), and
  the payload `session_id` is accepted under both observed semantics (0.150
  parent identity, 0.151 child self-identity) with any third identity still
  refused. Every decline now records a content-free refusal slug surfaced in
  the restricted-canary identity injection, and an opt-in
  `AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS=1` mode names the declining branch.
  Focused tests cover derivation-when-hint-missing, both session semantics,
  and refusal naming. Live `verify-activation` rides the next production
  install and the operator's fresh attended trust.
- 2026-08-30 live isolation after the `5459794d` install and fresh attended
  trust: the join fixes advanced the restricted canary past the silent
  declines — the SubagentStart handler now runs to a staffing decision — but
  the child was staffed through the ordinary native-child path
  (`native_child_inference`, child-judge selection) instead of the pinned
  canary team, so delivery verification refuses the decision
  (`host_child_collection_reason=verification_refused`) and the parent
  projection reports `native_collaboration_topology_invalid` with
  `child_interaction_count` 0. Every prior refusal channel is unobservable on
  0.151 (hook stderr swallowed, hook stdout encrypted into the child
  rollout), so the diagnostics-armed canary now writes the join outcome —
  payload field-name census, refusal slug, agent-type admission — to a
  private host-side sink surfaced as `hook_join_diagnostics` on the canary
  record, and the join absorbs the SubagentStart rollout-flush race with two
  bounded re-reads. The complete real 0.151 child rollout replays to its
  exact parent through `codex_v1491_child_parent_session` with the recorded
  session cwd, so the artifact contract itself holds.

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
- [x] Version-scoped fixtures from real 0.151 rollouts cover parent and child
      projections.
- [ ] `agency install --agent codex --verify-activation` exits 0 with a fresh
      persisted attestation on 0.151.
- [x] 0.150 contracts remain green.
