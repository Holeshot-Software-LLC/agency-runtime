---
title: "AR-333: Report the unsupported Codex isolated-profile agency canary loudly"
status: open
category: roadmap
created: 2026-08-29
updated: 2026-08-29
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

- [ ] Readiness no longer reports `ready=true` for a combination whose
      execution deterministically refuses.
- [ ] The refusal carries a stable content-free reason distinct from runtime
      invocation failures.
- [ ] A focused test covers the isolated-profile agency-mode combination.
