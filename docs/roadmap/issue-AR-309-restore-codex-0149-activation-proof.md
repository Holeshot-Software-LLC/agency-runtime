---
title: "AR-309: Restore Codex 0.149 activation proof"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, native-child, evidence, headers]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-308-bind-activation-canary-delegation.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/adapters/hooks.py
  - tests/test_codex_activation_canary.py
  - tests/test_host_hooks.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-309
priority: p0
tracker_url: null
depends_on: [AR-308]
blocks: [AR-297]
---

# AR-309: Restore Codex 0.149 activation proof

## Problem

The first exact post-AR-308 Codex 0.149.1 managed-policy canary now resolves
the inference-owned route and executes one direct native child, but the
installed proof boundary cannot admit the result. The forced
`multi_agent_v2` rollout stores the child start inside the newer
`event_msg/item_completed/SubAgentActivity` envelope, redacts the decrypted
child launch text from the child rollout, and does not place Agency's
post-wait header snapshot in the parent context. The parser therefore reports
no collaboration projection, the host-authored card-delivery contract has no
visible launch marker, and the parent copies the stale initial
`Agency/Agencies delegated: none` line into a response that Stop rejects.

## Current state

- Exact candidate `1f32915d14a9760d8cd12d21fbc6e7f3d8940a66` uses
  config SHA-256
  `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`.
  The no-bypass managed-policy install JSON is mode 0600 at SHA-256
  `72c4ba033bb87234db6f4470d88e52e3d2c2f2cd483fbb1b32a67a2747d6e4ab`;
  stderr is empty and the command exits 1.
- Session `01a03f83-bb05-7c43-b9b3-38cb8d9e30dd` and trace
  `01a03f83-bb12-7d80-b95a-879bce00b338` prove one accepted
  `code-reviewer` route, one loaded specialist, one delegated native task, one
  completed child answer, one completed wait, and one finalization. The route
  is `delivery=delegate`, so AR-308 crossed its exact former blocker.
- Parent and child rollouts are retained mode 0600 at SHA-256
  `5a548331ecd42e382510f9efbecf5b280e9195333c8f25ebf8290fbbb0412af2`
  and
  `4732afb2f94dadaed62bc6b0548bac3a6937b751eba8c583f85ab1ab8f0e225e`.
  The parent records `spawn_agent`, `SubAgentActivity(kind=started)`,
  `wait_agent`, and the child's conclusion. The child artifact contains no
  workforce-card marker or work-unit text before first speech.
- The parent final response carries a syntactically complete five-line header
  but falsely retains `delegated: none`. Store finalization
  `b5cf0953-e7b8-4700-8fa5-a319d420fb93` is therefore
  `response_invalid` with missing `evidence_verification`; no attestation is
  persisted.
- Codex 0.149.1 reports both `multi_agent` and `multi_agent_v2` as stable,
  with `multi_agent` enabled and `multi_agent_v2` disabled by default. The
  current canary overrides that native default and forces V2.
- The bounded supported-`multi_agent` comparison exits 0, but it cannot
  replace V2. Session `01a03f94-156b-75f1-9022-ea7cef6ace55`, trace
  `01a03f94-15cb-7192-bf4e-34f518c4798a`, and query SHA-256
  `4d160cfe3770d67ea8246cc096d9d47c665cb589ad6b140970de6dfc67d0c652`
  record the same accepted `code-reviewer` route with
  `delivery=delegate`, but zero native routes, deliveries, delegations, or
  worker runs. The injected host context carries only the generic instruction
  to follow a plan, not an actual `[AGENCY DELEGATION PLAN]` row, so the
  truthful first response reports `delegated: none` and does not spawn.
- The stable diagnostic stdout, stderr, Store snapshot, and parent rollout are
  retained mode 0600 at SHA-256
  `356d36d14a66702a05f82c00997c0e90268e307a0a888cc4647aea7e4e306bc6`,
  `dc6b65253c32f61f8551adfbf795546e6ed20d353aa0686024692d4415e73f5a`,
  `bb518e7cd3157bee97c408c4b0d140f8b7928a5c94ecf7b7ebbbe5fff642b20d`,
  and
  `953295259aa29014719af67e930a7e4315cbdcc40eda226ca971bee3962790a3`.
  Stderr contains only the Codex remote-plugin OAuth transport-close warning.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

The supported stable surface does not restore the required delegation, so keep
the only surface that executes the accepted native plan and repair the exact
Codex 0.149 V2 evidence boundary. Update the rollout parser only for the exact
allowlisted `event_msg/item_completed/SubAgentActivity` envelope and retain
one-child cardinality plus invocation-window checks.

Because Codex deliberately redacts the decrypted launch message from the child
rollout, bind an unpredictable hook-generated one-use receipt to the exact
decision, child, work-unit/card digest, and invocation. Require the child to
return that receipt in its first host-persisted response before any parent
acceptance. The parent must not receive the clear receipt before spawn, and
Store state or parent prose remains insufficient by itself. Supply a
plan-derived conditional final-header contract before spawn, but accept it only
when host collaboration plus delivery evidence agree and the first parent
finalization passes. Record the durable authority change before implementation;
do not weaken ADR-0156 or activate a trust bypass.

## Dependencies

- ADR-0156 requires the native host, not Agency's Store, to originate card
  delivery proof.
- ADR-0173 requires a normal managed-policy invocation, exact native child,
  valid first-pass response, and persisted attestation.
- AR-308 supplies the now-live `delegate` execution contract.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] One clean exact canary proves AR-308's accepted delegate route and sole
      native spawn/wait before failing at the later Codex 0.149 boundary.
- [x] Exact parent and child host artifacts, Store identifiers, exit, hashes,
      and missing proof fields are retained without a secret.
- [x] A bounded stable-surface diagnostic determines whether supported Codex
      behavior restores visible pre-speech delivery and post-wait context.
- [ ] The exact Codex 0.149 rollout envelope is parsed without accepting an
      ambiguous parent, child, tool sequence, or invocation window.
- [ ] A host-authored artifact proves the exact selected workforce card reached
      the sole child before speech; Store state and parent prose remain
      insufficient by themselves.
- [ ] The first parent final response carries current delegated evidence,
      Stop accepts it without correction, and the managed canary persists an
      attestation with no trust bypass.
- [ ] Focused warning-strict tests, decision conformance, and every named
      repository gate pass on the rebuilt exact candidate.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
