---
title: "AR-324: Bind the Codex canary child through host-authored lineage"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, hooks, native-child, security, artifacts]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_canary_activation_snapshot.py
  - tests/test_child_delivery_evidence.py
  - CHANGELOG.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-324
priority: p0
tracker_url: null
depends_on: [AR-310, AR-313, AR-314, AR-322]
blocks: [AR-297]
---

# AR-324: Bind the Codex canary child through host-authored lineage

## Problem

The AR-322 request digest is correct for the exact parent canary, but a rebuilt
Codex `0.149.1` child still receives only the generic identity context. The
child hook therefore records no native-child route or delivery even though the
parent route is exact and accepted and the native child exits successfully.

## Current state

- Exact `c7f35dd5` install receipt `999f3005...33269` exits 1 after an exit-0,
  non-timeout Codex invocation. Parent route `f26e582f...dd39` selects only
  `code-reviewer`, but child route/delivery/activation cardinalities remain 0.
- Parent rollout `55ee6a9c...01a5`, child rollout `76f86896...a218`, and Store
  `06e777f0...0f08` show child `01a041ac...ce9b` received `generic-worker`.
- The task bytes hash to the persisted query hash
  `cee32889...b205`, ruling out a parent request-digest calculation error.
- Official `rust-v0.149.1` commit `ff29a443...9ea4` snapshots the process
  environment per hook session. It constructs `SubagentStart.session_id` from
  the root session and `agent_id` from the spawned child thread. The child's
  host-authored `session_meta` independently records that child plus the parent
  as `session_id`, `parent_thread_id`, and nested thread-spawn parent.
- The bounded reader now admits only the exact canonical UUIDv7, path,
  owner-integrity, version, origin, schema, depth-one, no-inheritance, timestamp,
  and three-parent agreement contract. Start reads the child transcript; stop
  reads the separately named agent transcript.
- Warning-strict focused artifact/snapshot/activation tests pass 137/137. The
  expanded canary, artifact, Store-file-trust, and turn-boundary set passes
  259/259; Ruff, metadata, policy availability, worklog generation, document
  validation for 889 Markdown files, and `git diff --check` exit 0.
- Clean ledger `9e8fa342` builds exact wheel `0d3c4948...dd4a` and five exact
  verified images. Fresh install `7197d5ff...a62` resolves accepted route
  `25e06734...7484` and child `01a041d3...b1d2`, which exits 0 without timeout,
  but again receives only generic identity. Retained parent/child rollouts and
  Store hash to `f83e31f3...02fc`, `b4215dc8...0394`, and
  `56518a59...53b0`.
- The live failure exposed ADR-0187's incorrect equality: hook `session_id` is
  the parent while `agent_id` is the child. The regression fails before and
  passes after the separate-ID join. Warning-strict focused sets pass 192/192
  and 258/258 with two expected skips; ADR-0188 supersedes ADR-0187.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Read only the exact leading `session_meta` record from the canonical active
Codex sessions root through the existing bounded, link-resistant, owner-trust
boundary. Pin the accepted record to Codex `0.149.1`, the hook child UUID, the
canonical rollout filename, `codex_exec`, MultiAgent V2, depth one, no inherited
history, and three agreeing parent fields. Require the hook's distinct child
`agent_id` to match the artifact child and its parent `session_id` to match all
three artifact parent fields. Use only that agreeing parent UUID to resolve one
live parent trace and exact accepted canary route. If the request digest is
present, require it to agree; never select a parent globally.

Apply the same lineage reader to `SubagentStart.transcript_path` and
`SubagentStop.agent_transcript_path`. Missing, malformed, linked, foreign,
version-drifted, ambiguous, terminal, or inconsistent artifacts fail closed to
the existing unstaffed identity behavior.

## Dependencies

- AR-310 owns the exact existing Store and active-run requirement.
- AR-313 owns normal-umask Codex artifact trust and link-resistant reads.
- AR-314 owns the exact `agent_type=default` discriminator.
- ADR-0156 and ADR-0179 still require host-authored v6 delivery and a one-use
  Store verification receipt; lineage alone proves neither.

## Acceptance

- [x] The exact `0.149.1` child artifact resolves one parent only when path,
      owner trust, child UUID, lineage fields, and version all agree.
- [x] The hook's root `session_id` and child `agent_id` remain distinct and
      agree independently with the artifact parent and child.
- [x] Missing, malformed, linked, foreign, wrong-version, inherited, nested,
      contradictory, terminal, and ambiguous cases fail closed.
- [x] A present request digest must agree with the parent route; ordinary and
      product processes receive no canary authority.
- [x] Focused warning-strict artifact, hook, snapshot, and security tests pass.
- [ ] A rebuilt fresh no-bypass Codex install proves v6 delivery, consumption,
      header, finalization, Store correlation, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
