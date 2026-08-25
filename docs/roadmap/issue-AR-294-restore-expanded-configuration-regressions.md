---
title: "AR-294: Restore expanded configuration regressions"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [testing, configuration, regression, release]
related:
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/RELEASE_CHECKLIST.md
  - tests/test_configuration.py
  - tests/test_security_config_store_coverage_complete_configuration.py
  - agency_runtime/core/config_defaults.yaml
  - agency_runtime/core/configuration_service.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-294
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-294: Restore expanded configuration regressions

## Problem

The post-merge expanded configuration run found two stale test fixtures. One
still expected the retired `fast` workforce default even though product defaults
and the current planning contract intentionally use `strict`. A low-level
configuration-service contract test called `apply_config_operations` without
the required narrowing dependency added by the existing write-only-changed-
paths repair. The named fast production spine did not include either file, so
both drifts had remained hidden while product behavior stayed correct.

## Current state

- `agency_runtime/core/config_defaults.yaml` and `WorkforceConfig` agree on the
  `strict` default with fast/balanced budgets of four and strict budget of five.
- Every production transaction caller supplies the narrowing function.
- The two failures occur only in expanded regression tests and reproduce on
  current remote `main` ancestry.
- Tracker creation remains pending explicit tracker authorization.

## Approach

Align the default-mode test with the canonical strict configuration and assert
all three stage budgets so the intended repair funding remains explicit. Supply
an inert narrowing seam to the low-level invalid-revision test; the tested
contract rejects the revision before any read, patch, narrowing, or write.

## Dependencies

- AR-293 caused the broader configuration/security suite to run but did not
  introduce either stale expectation.
- The existing strict-mode and narrowed-persistence decisions remain unchanged.

## Acceptance

- [x] The default configuration regression asserts strict mode and exact fast,
      balanced, and strict call budgets.
- [x] The low-level invalid-revision regression supplies every current service
      dependency and still fails before transaction work.
- [x] Both tests fail before this fixture-only correction and pass afterward.
- [x] The expanded merged Python spine, Ruff, docs, UI, routing, decision-
      conformance, and diff gates pass.
- [x] Tracker creation and linkage remain pending explicit tracker
      authorization.

## Verification evidence

Before correction, the merged expanded run completed with 1,125 passed, 21
skipped, and exactly these two failures. Neither traceback entered product
execution: one compared a stale expected string and the other raised Python's
missing-keyword `TypeError` while constructing a direct test call. Focused and
expanded post-fix results are recorded in the AR-294 worklog checkpoint.
