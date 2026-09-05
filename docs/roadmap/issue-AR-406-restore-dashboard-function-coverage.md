---
title: "AR-406: Restore the configured dashboard UI function-coverage gate"
status: done
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [dashboard, testing, coverage]
related:
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/acceptance/issue-AR-406.md
  - docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md
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

Measurement audit: the failing aggregate includes the test file itself. Raw
V8 output has 704 test-function entries, 86 unexecuted, including unused mock
callbacks. All seven shipped product modules already pass unchanged floors:
96.92 percent lines, 86.62 branches, 95.71 functions. ADR-0220 corrects the
denominator using the same recursive production selector in local and CI gates.
Two new exact-command regression cases first fail on missing scope, then guard
the complete selector, test invocation and unchanged floors. No UI source or
behavioral test is changed. All three candidate-bound criteria are satisfied
at d109b094. The first missing-baseline-comparison verdict remains in history;
the second evidence packet supplies exact matching production-tree and UI-test
Git objects without changing criteria or implementation. PR #684 merged on
2026-09-05 at 853de3106ebc74f3ba6c977722d98f06a969c9c2. Tracker #682 was
then closed as completed at 21:35:56 UTC; its closed state was read back.

```text
node --test --experimental-test-coverage --test-coverage-lines=95 \
  --test-coverage-branches=86 --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

## Approach

Measure the production JavaScript folder, including nested modules, in both
configured gates. Keep all 138 UI cases, every shipped module and the 95/86/93
floors. Pin local/CI command parity with a regression for each entry point.
Retain the original mixed-scope failure and show the complete production-only
report; this changes measurement scope, not product behavior or coverage quality.

## Dependencies

Existing UI harness and current configured local/CI coverage command. No
Windows run or exhaustive Python workflow is required for this Linux package.

## Acceptance

- [x] The exact configured dashboard UI coverage command passes all existing floors.
- [x] Local and hosted gates include every production dashboard JavaScript module, with regression checks preventing narrower scope or lower floors.
- [x] Production semantics and existing UI behavioral tests remain unchanged; all tests, including the listener soak and teardown checks, pass.

## Superseded working assumption

The initial proposal required added callback tests and unchanged exclusions.
Its original second criterion was: "Added callback coverage asserts visible
behavior and lifecycle cleanup, including relevant failures, rather than mere
invocation." Its third was: "Production semantics, coverage floors and exclusions
remain unchanged." Those provisional requirements assumed missing product
coverage before the measurement scope was inspected. ADR-0220 replaces that
assumption with an explicit production-wide measurement contract. Numeric floors
and production scope are not reduced; test fixtures leave the denominator.
No earlier isolated verdict or historical result is rewritten.
