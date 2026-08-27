---
title: "AR-320: Bound the Codex wait to the full child staffing path"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [bug, codex, canary, native-child, timeout, reliability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-318-bound-codex-activation-child-wait.md
  - docs/roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0184-bound-codex-wait-to-full-child-staffing.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_staffing.py
  - tests/test_codex_activation_canary.py
  - tests/test_canary_coverage_complete.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-320
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-320: Bound the Codex wait to the full child staffing path

## Problem

The exact activation canary permits one initial native-child judge call and one
funded abstention-repair call. Each pinned profile call is validly bounded at
120 seconds, but the parent waits only 120 seconds for the entire hook and
child turn. A legal two-call staffing path can therefore outlive the parent's
single wait even though both inference calls finish successfully.

## Current state

- Exact `89a56901` absence receipt `a56ac1c5...d994` passes in fresh container
  `f72c1b51...0555`; install `96e4d746...73cf` exits 1 without a bypass.
- The parent accepted `code-reviewer` at 104,114 ms, spawned child
  `01a04131...7490`, and issued one 120,000-ms wait. That wait returned
  `timed_out=true` at 03:11:18Z; the child hook completed immediately after it.
- Owner journal `a32aa50c...edc2` proves two sequential, untruncated Mistral
  requests: 20,059 tokens in 62,057.76 ms and 20,145 tokens in 62,870.53 ms.
  The second is the one funded abstention repair, not a retry of a failure.
- The child rollout receives no v6 delivery, receives identity only at
  03:11:23Z, and is then interrupted. Store, parent rollout, and child rollout
  hash to `d8755fd9...2f72`, `00d8e1d5...8076`, and `e978545c...d00a`.
- The approved LiteLLM alias, free Mistral model, endpoint, timeout, and no-
  fallback pin are known and unchanged. Tracker creation is prohibited.

## Approach

Bind the exact Codex activation protocol to one 300,000-ms wait: two validated
120,000-ms judge calls plus a fixed 60,000-ms margin for hook completion and the
native child's bounded response. Keep the 600-second outer install ceiling,
one spawn, one wait, no follow-up, no retry, and every existing delivery,
Store, header, finalization, and attestation requirement. Reject the superseded
120,000-ms rollout shape as stale.

## Dependencies

- AR-319 owns the separate aggregate judge budget and proves each request may
  use the profile's existing 120-second ceiling.
- Native child staffing deliberately funds exactly one abstention repair.
- ADR-0179 still requires exact host-authored v6 delivery before child speech.

## Acceptance

- [ ] Prompt and rollout validation require exactly one 300,000-ms wait while
      rejecting the superseded 120,000-ms shape.
- [ ] Focused warning-strict canary, staffing, and coverage tests pass.
- [ ] A rebuilt fresh Codex production-container install proves delivery,
      consumption, first accepted finalization, header, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
