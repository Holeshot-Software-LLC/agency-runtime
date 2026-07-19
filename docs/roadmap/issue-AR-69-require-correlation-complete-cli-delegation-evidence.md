---
title: "AR-69: Require correlation-complete CLI delegation evidence"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [delegation, cli, evidence, correlation, observability, testing]
related:
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-69
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/70
depends_on:
  - AR-27
blocks: []
---

# AR-69: Require correlation-complete CLI delegation evidence

## Problem

The `agency delegate` CLI could persist a completed delegation with a generated
trace but empty session, work-unit, backend, worker, and native-run identities.
That row looked like execution evidence while remaining impossible to reconcile
to one request, one planned unit, or one observed worker.

## Current state

The CLI is being routed through the same strict mutation contract as host and
MCP delegation. Suggestions remain suggestions; positive execution states
require complete session, trace, stable work-unit, backend, worker-kind, and
concrete native worker correlation.

## Approach

Allocate a bounded CLI session and stable task-derived work-unit before spawn.
Record the resolved backend and executable identity plus an observed host
response or process identifier only after execution. Reject any public Store
mutation that attempts to persist started, delegated, running, or completed
state without those fields, while keeping failure and skipped blocker evidence
truthful and free of fabricated worker identity.

## Dependencies

AR-27 establishes authoritative delegation mutation and Stop enforcement. This
item closes the remaining direct CLI path that could bypass that evidence
contract.

## Acceptance

- [x] CLI delegation allocates non-empty session, trace, and stable work-unit IDs.
- [x] Completed rows identify the real backend, worker kind, worker, and native run.
- [x] A requested specialist slug is never used as proof of a spawned worker.
- [x] Positive execution states without complete correlation fail closed.
- [x] Failed, skipped, suggested, JSON, timeout, and missing-backend paths stay truthful.
- [x] CLI, Store, delegation, full-suite, exact-coverage, and installed smoke gates pass.
