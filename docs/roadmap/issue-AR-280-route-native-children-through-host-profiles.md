---
title: "Route native children through host-scoped inference"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [native-child, openclaw, hermes, inference, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
  - agency_runtime/core/native_child_staffing.py
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/core/installer_payload_hermes.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-280
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119, AR-281]
---

# AR-280: Route native children through host-scoped inference

## Problem

OpenClaw and Hermes parent workforce turns resolve their harness-scoped Agency
inference profiles, but their native-child boundary does not yet preserve the
same contract. Native-child staffing passes the unprojected configuration to
the judge, so it can bypass `inference.harnesses.<host>` and silently reach a
legacy provider. The generated bridges also assume child identity fields that
the installed OpenClaw 2026.7.1-2 and Hermes v0.20.4 hooks do not emit.

Running a live child test in that state could prove that a host spawned a child
while saying nothing reliable about which Agency provider staffed it or whether
the selected cards reached that child.

## Current state

- Parent workforce inference is live on both hosts through profile
  `linux-task-agency-router`, provider type `litellm`, and requested alias/model
  group `task-agency-router`.
- OpenClaw exposes `sessions_spawn`. Its pre-tool hook carries the parent
  session, parent run, host tool-call identity, and exact task before execution;
  its later spawn event does not carry the parent session or task assumed by the
  generated plugin.
- Hermes exposes `delegate_task`. Its start hook carries both child session and
  subagent identities, while child preflight and stop carry the child session
  but omit the subagent identity assumed by the generated plugin.
- Store lifecycle rows or child prose cannot independently prove Rule 4 card
  delivery. OpenClaw and Hermes still lack bounded host-artifact collectors
  under ADR-0156, so that matrix limitation must remain explicit even after an
  operational native-child proof.
- Focused implementation now projects the owning host profile, staffs and
  binds OpenClaw's real `sessions_spawn` boundary, and keys Hermes lifecycle
  correlation by its real child session. It also gives OpenClaw's outer child
  process the selected host profile's bounded deadline while leaving Hermes's
  existing judge and hook deadlines unchanged, and can reconcile a child end
  from durable Store joins when process-local correlation is gone.
- AR-281 separately finalizes OpenClaw's authenticated completion send against
  the original parent trace. The combined focused gate passes 299 tests with
  one existing skip. Clean checkout `27e9ec62` was installed through Agency's
  OpenClaw installer only while the gateway was natively stopped, then the
  gateway restarted natively with RPC healthy and all 12 hooks loaded.
- The installed bundle/runtime digest is `0c2bb3fc...`; launcher SHA-256 is
  `e9169d04...`. Native `litellm/task-general` plus six fallbacks and every
  semantic native-config leaf are unchanged. Hermes remains active with its
  config, environment, and launcher hashes unchanged.
- Fresh OpenClaw parent `a0f349c8...` / trace `856341f9...` spawned native
  worker `e0ee5df5...` / run `b182db5c...`, which executed and completed its
  read-only task. Native-child route `native-child-eaa40...` proves one applied
  `linux-task-agency-router` / `litellm` / exact `task-agency-router` attempt,
  zero cross-provider fallback, and no actual-model telemetry.
- Parent return did not pass. Ready-receipt integrity assumed one total routing
  row and rejected the valid auxiliary `native_child_inference` row before
  completion could queue to Telegram. Identity resolution passed; cleanup,
  restart/reload, timeout, TTL, and mismatch are ruled out. The locally green
  fail-closed correction admits exactly one canonical route plus only unique,
  strictly re-projected child-success routes while validating exact route IDs,
  canonical timestamps/context digests, exact numeric types, and canonical JSON.
  Independent Critical/High review is green after closing those gaps.
- Focused 113/1, named spine 848/3, docs 780/worklog 1,155, Ruff 682,
  dashboard UI 134, routing eval, full decision-conformance baseline plus
  160/160 mutations killed with zero survived/invalid and source unchanged, and
  diff check all pass. Private-HOME/no-`pytest` and trusted-interpreter eval
  failures are retained; the owner-private `/usr/bin/python3` eval environment
  passes. No exhaustive workflow corpus ran. The candidate is uninstalled and
  unproven live pending a clean checkpoint and Agency-only reinstall.

## Approach

1. Resolve the native-child judge provider chain through the exact owning host
   before either first-pass or repair inference, preserving explicit canary
   provider pins.
2. Staff OpenClaw `sessions_spawn` at its host-authenticated pre-execution tool
   boundary, bind delivery to the tool-call launch identity, and rewrite only
   the exact child task before the host launches it.
3. Correlate OpenClaw's accepted tool result and end hook to the real child
   session/run without guessing absent spawn-event fields.
4. Correlate Hermes child preflight and stop through the exact child session
   retained from `subagent_start`, including ambiguity and parent checks.
5. Reinstall Agency only, one host at a time, then run one fresh harmless native
   child per host and preserve parent, provider, routing, delegation, lifecycle,
   and response-delivery evidence.

## Dependencies

- The existing host-scoped LiteLLM profile and alias remain unchanged.
- Native OpenClaw and Hermes configuration, model routing, source, and versions
  remain unchanged.
- Tracker creation requires separate authorization and is intentionally
  pending; no outward-facing write is part of this package.
- Strict Rule 4 promotion additionally requires a host-authored artifact parser
  and immutable delivery-verification receipt for each host.

## Acceptance

- [x] Focused regressions use the installed hosts' real child hook fields and
      fail against the pre-fix generated bridges.
- [x] OpenClaw native-child staffing occurs before `sessions_spawn` executes,
      retains all non-task parameters, and binds the accepted child session/run
      to the exact parent session/run and launch identity.
- [x] Hermes child preflight and stop resolve the exact host-issued child
      session without inventing an absent subagent field.
- [x] Both native-child judge attempts resolve the owning host automatically to
      profile `linux-task-agency-router`, provider type `litellm`, and requested
      alias/model group `task-agency-router`, with zero cross-provider fallback.
- [x] OpenClaw's generated bridge derives its bounded outer child deadline from
      the selected host profile and can close lifecycle evidence through exact
      durable Store correlation after process-local state loss.
- [x] The combined focused implementation gate passes 299 tests with one
      existing skip and does not modify any host configuration.
- [x] Agency-only OpenClaw installation from clean checkout `27e9ec62` passes
      stopped-gateway, launcher-provenance, native restart, RPC, and 12-hook
      activation checks without native-route or semantic-config drift.
- [x] A fresh OpenClaw native child uses the host-scoped LiteLLM profile with
      exact alias/model-group and zero fallback, then executes and completes.
- [x] The ready-receipt correction passes independent Critical/High review and
      the focused, fast-spine, docs, Ruff, dashboard, routing, and full
      decision-conformance gates.
- [ ] Checkpoint the locally green correction and reinstall it through Agency
      only while OpenClaw is natively stopped.
- [ ] Fresh live OpenClaw and Hermes native children spawn, complete, and return
      to their parents with correlated Store lifecycle evidence.
- [x] Rule 4 remains `unproven` unless an ADR-0156-compliant host-authored
      pre-speech artifact produces a `native_child_delivery_verifications` row.
- [x] Codex OAuth/configuration and canary, Claude, ZCode, native host configs,
      and host-native model routes remain untouched.
