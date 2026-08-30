---
title: "AR-333: Report the unsupported Codex isolated-profile agency canary loudly"
status: done
category: roadmap
created: 2026-08-29
updated: 2026-08-30
tags: [bug, host-integrations, codex, canary, diagnosability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-333
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/347
depends_on: []
blocks: []
---

# AR-333: Report the unsupported Codex isolated-profile agency canary loudly

## Problem

`agency host-canary codex --execute --mode agency` with the default
isolated-profile scope always fails: `canary_proof.invoke_and_collect_evidence`
routes every `_SafeCodexCanaryBackend` through `execute_with_host_delivery`,
whose restricted contract requires current-profile scope, an existing Store,
and the exact activation rollout, so it deterministically raises before any
child launch. The exception is swallowed into the fixed content-free error
"safe host invocation failed before evidence could be evaluated", while the
readiness report for the same flags says `ready=true`.

## Current state

- 2026-08-29 receipts in
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/`:
  `codex-canary-execute.json`, `codex-canary-execute-2.json`, and
  `codex-canary-execute-4.json`, plus `codex-canary-debug-traceback.txt`
  showing `ValueError("Codex host-delivery collection requires the restricted
  canary")` from `canary_backends.py` via `canary_proof.py`.
- Zero model calls were spent; the refusal is deterministic and precedes the
  child invocation.
- Diagnosing required attaching a debug handler to
  `agency_runtime.core.canary_proof` because the CLI configures no logging
  handler, so the designed `logger.debug(..., exc_info=True)` escape hatch is
  unreachable in ordinary operation.
- The supported Codex path is the restricted current-profile canary, which
  requires completed attended trust; that ordering is by design and stays.
- Code landed 2026-08-30: `invoke_and_collect_evidence` gates host-delivery
  collection on the backend's `current-profile` scope, so the isolated-profile
  agency canary now runs through plain `execute()` and its evidence carries
  the stable content-free reason `unsupported_profile_scope` instead of
  refusing before launch. Readiness `ready=true` for the combination is now
  truthful because the combination executes. A focused test drives a real
  `SafeCodexCanaryBackend` through the collection gate and proves the plain
  path plus the recorded reason. Live-proven 2026-08-30 on the `5459794d`
  install: the isolated-profile agency canary launched a real turn (spawn
  and accepted finalization) instead of refusing pre-launch
  (`codex-canary-isolated-5459794d.json`).

## Approach

Make readiness for Codex agency mode with isolated-profile scope report the
unsupported combination instead of `ready=true`, or route that combination to
plain `execute()` without host-delivery expectations. Distinguish a
deterministic contract refusal from a runtime invocation failure with a stable
content-free reason, and document how to surface the debug traceback.

## Dependencies

None. Do not weaken the restricted-canary contract or the attended trust
requirement.

## Acceptance

- [x] Readiness no longer reports `ready=true` for a combination whose
      execution deterministically refuses (the combination now executes
      through plain `execute()`).
- [x] The refusal carries a stable content-free reason distinct from runtime
      invocation failures (`host_child_collection_reason` =
      `unsupported_profile_scope`).
- [x] A focused test covers the isolated-profile agency-mode combination.
