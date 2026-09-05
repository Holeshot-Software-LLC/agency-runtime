---
title: "AR-406: Restore the configured dashboard UI function-coverage gate"
status: open
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [dashboard, testing, coverage]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - tests/dashboard_ui.test.mjs
  - scripts/run_local_gates.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-406
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/682
depends_on: []
blocks: []
---

# AR-406: Restore the configured dashboard UI function-coverage gate

## Problem

All dashboard UI tests pass, but the current configured function-coverage floor
does not. This is shared verification debt, not proof that every old dashboard
defect is still present.

## Current state

At main e425583603a99debc5b6cdbe3c2c84f4f3e7954d, Node v22.23.2,
the exact command exits 1 after 138 passing tests: lines 97.80 percent,
branches 88.43 percent, functions 91.12 percent. Floors are 95/86/93.
The AR-152 fifty-render listener regression passes. AR-144's July completed
coverage repair remains historical evidence, not a current-build pass.

```text
node --test --experimental-test-coverage --test-coverage-lines=95 \
  --test-coverage-branches=86 --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

## Approach

Inspect the measurement scope and missing bound callbacks. Add behavioral
assertions for meaningful user-visible state, failures and lifecycle cleanup;
do not invoke callbacks only to raise a percentage, lower floors or exclude
files to turn the gate green. Keep this separate from already-shipped defects.

## Dependencies

Existing UI harness and current configured local/CI coverage command. No
Windows run or exhaustive Python workflow is required for this Linux package.

## Acceptance

- [ ] The exact configured dashboard UI coverage command passes all existing floors.
- [ ] Added callback coverage asserts visible behavior and lifecycle cleanup, including relevant failures, rather than mere invocation.
- [ ] Production semantics, coverage floors and exclusions remain unchanged.
