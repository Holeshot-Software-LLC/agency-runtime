---
title: "Separate Codex hook parent and child identities"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, lineage, security, artifacts]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - agency_runtime/adapters/hooks.py
  - tests/test_canary_activation_snapshot.py
supersedes: []
superseded_by: null
type: worklog
commit: 34f41532bbc700e8b824b63a322ac6261fedba9b
short: 34f41532
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
---

# Worklog detail: Separate Codex hook parent and child identities

## Purpose

Repair the exact `9e8fa342` no-bypass Codex production-container canary after
the valid host-authored child lineage still produced generic identity and zero
delivery. Preserve the strict artifact, route, consumption, finalization, and
attestation gates.

## Approach

The restricted `0.149.1` child hook now validates its two host identities
separately. `SubagentStart.session_id` is the claimed root parent and
`agent_id` is the claimed child thread. The child must match the exact bounded
rollout filename and leading metadata; the hook parent must match all three
independently authored rollout parent fields. Only that agreement scopes one
live exact Store route. The request digest remains an optional narrowing check.

Every malformed, equal, foreign, contradictory, ambiguous, or terminal identity
still fails closed to the existing generic unstaffed behavior. The join grants
no delivery or finalization authority by itself.

## Challenges encountered

The exact child rollout passed the new lineage reader when inspected directly,
and upstream recorder ordering proved the metadata was flushed before the start
hook. Inspection of the supported hook construction then exposed the mismatch:
Codex derives `session_id` from the root session but derives `agent_id` from the
spawned thread. ADR-0187's equality check therefore rejected every real child
before reaching the otherwise valid parent join.

## Decisions and alternatives

[ADR-0188](../decisions/0188-separate-codex-hook-parent-and-child-identities.md)
supersedes ADR-0187's field equality while preserving its bounded artifact
authority. Trusting either hook fields or rollout lineage alone, using the
child turn ID as parent authority, and selecting a global open run remain
rejected.

## Verification

- The regression fails twice before the code change and passes twice after it.
- The warning-strict lineage/activation set passes 192/192.
- The separate warning-strict hook, activation, and security set passes 258/258
  with two expected skips.
- Ruff check/format, metadata, policy availability, document validation, and
  `git diff --check` pass before the checkpoint ledger.
- Retained exact parent/child rollouts and Store hash to
  `f83e31f3...02fc`, `b4215dc8...0394`, and `56518a59...53b0`.

## Follow-ups

- Rebuild exact artifacts/images from the clean ledger and run one new no-bypass
  Codex production-container transaction; never reuse the failed container.
- Continue the remaining harness, ordinary-process, host/dashboard, gate, and
  teardown packages under AR-297.
- Tracker creation remains prohibited until the owner explicitly authorizes it.
