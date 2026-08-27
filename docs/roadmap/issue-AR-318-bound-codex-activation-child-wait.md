---
title: "AR-318: Bound the Codex activation child wait above observed latency"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [bug, codex, canary, containers, reliability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0184-bound-codex-wait-to-full-child-staffing.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - tests/test_codex_activation_canary.py
  - tests/test_canary_coverage_complete.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-318
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-318: Bound the Codex activation child wait above observed latency

## Problem

The exact no-bypass Codex production-container canary gives its sole native
child one 60-second `wait_agent` window. The exact child can finish at that
boundary, causing a false activation failure after Agency has resolved the
route and the native child has completed its work at exit 0.

## Current state

- Superseded candidate `8d33694c` reaches accepted route `d1a4e01f...7565` and
  child `01a04100...e872` without a bypass under config `a4e213d6...97348`.
- The child authors its terminal message 224 ms before the parent's single
  60-second wait returns `timed_out=true`. The parent then truthfully reports
  failure, so there is no native delivery, consumption, accepted finalization,
  header, or attestation.
- Install receipt `2942f5ee...935b`, Store `3f3f5d84...397e`, parent rollout
  `ec0c7859...d523`, and child rollout `fc2c7681...d8f9` are retained mode 0600.
- The shared 120,000-ms source contract now drives both the Codex developer
  instruction and exact direct-rollout validator. The stale 60,000-ms shape is
  regression-rejected; Ruff and 309 focused warning-strict tests pass at exit 0.
- Repaired ledger `c6b7d92d` canonical build, strict Twine, independent
  verification, and five-image label/version verification exit 0. Wheel
  `704e78a9...79a8` and image receipt `676b83dd...5c2b` are retained mode 0600.
- Fresh `c6b7d92d` live evidence emits the exact 120,000-ms wait, observes child
  completion, and returns `timed_out=false`. AR-319 owns the downstream pinned
  judge timeout that still prevents full v6 admission.
- Fresh `89a56901` evidence proves the full legal child-staffing path may make
  two successful inference calls totaling about 125 seconds. ADR-0184
  supersedes the 120-second decision; AR-320 owns the new exact bound.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Define one shared activation-canary wait constant at 120,000 ms. Use it in the
tool-reduced Codex developer contract and the exact rollout validator, while
retaining exactly one spawn, one wait, no follow-up, no retry, and the existing
600-second outer production-install ceiling. Reject the former 60,000-ms shape
as stale rather than weakening terminal-completion evidence.

## Dependencies

- ADR-0173 requires a fresh normal invocation and does not admit a trust bypass.
- ADR-0179 still requires the exact host-authored child artifact and consumption.
- The fix changes only the bounded native wait; it does not change models,
  staffing, delivery, Store authority, or finalization criteria.

## Acceptance

- [x] Prompt and rollout validation require exactly one 120,000-ms wait.
- [x] Focused warning-strict canary and coverage tests pass.
- [ ] A rebuilt fresh Codex production-container install produces the required
      delivery, consumption, first accepted finalization, header, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
