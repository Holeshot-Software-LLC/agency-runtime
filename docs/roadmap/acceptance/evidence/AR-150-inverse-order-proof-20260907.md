---
title: "AR-150 direct inverse refresh-order proof"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, concurrency, acceptance, regression]
related:
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/acceptance/evidence/AR-150-refresh-epochs-20260907.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - tests/dashboard_ui.test.mjs
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-150 direct inverse refresh-order proof

## First review and bounded response

The first isolated review of 57c225c1 supplied satisfied verdicts for criteria
1/3/4 and absent for criterion 2: the cited roster-intent and uncontested-refresh
tests did not directly demonstrate inverse refresh-response ordering. The
complete verdict table is preserved at 4e820ff4. This is an evidence gap, not a
reproduced runtime defect or a relabeled first-pass success.

Four direct tests are added at `tests/dashboard_ui.test.mjs:496-579`.
All product and browser-checker bytes remain unchanged from 2ecde1a5:
`git diff --exit-code 2ecde1a5 -- agency_runtime scripts` returned zero.
Within tests, only `tests/dashboard_ui.test.mjs` differs. No previous assertion,
coverage floor, request guard or cancellation behavior is removed.

## Direct inverse-order matrix

The older scope is either workforce refresh or full refresh; the newer intent
uses the other scope. Each direction runs both older-first and newer-first
response completion. Workforce, hiring, control and live payloads carry
distinct older/newer revision identities.

The network double intentionally returns each response after its signal was
aborted. Each test requires the obsolete invocation to return false and the
new invocation to return true. When the obsolete result arrives first, worker,
hiring, control and live state must remain at the baseline until the new result.
After both finish, worker/hiring values and collection revisions must all be
newer; control/live revisions must be newer only when the latest scope is full,
otherwise their baseline must remain. Request ownership must be released.

This directly checks that neither response order combines an old worker/hiring
payload with a new full snapshot, or an obsolete full snapshot with new
workforce intent. It exercises existing shared epoch/controller guards without
substituting cooperative abort behavior for the stale-response assertion.

## Current checks

Focused direct test command:

```bash
node --test --test-name-pattern='inverse .* refresh order' tests/dashboard_ui.test.mjs
```

Result: 4 passed, zero failures/skips, 70.63ms.

Complete current source-only UI coverage command:

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Result: **176 passed**, zero failures/skips, **207.19ms**. Product coverage:
**96.93% lines / 86.70% branches / 95.71% functions**, above the unchanged
95/86/93 floors. All seven production JavaScript modules remain included.

This package's server/auth/transaction run passed 180 in 28.82s before the
test-only addition; no Python test or runtime changed. The first evidence
record retains that exact command/result. The earlier named spine and
decision-conformance reports remain scoped reuse, not new executions.

## Unchanged browser behavior

The [repaired installed-wheel receipt](AR-138-repaired-dashboard-20260907.md#browser-evidence)
still matches all ten dashboard asset bytes and the server code. Its 21 loaded
view/viewport checks, real poll focus/selection/disclosure preservation and
visible stale-failure recovery remain applicable same-byte evidence, not a
fresh install claim. No native Windows/host, full WCAG or screen-reader claim.

## Acceptance boundary

The second candidate requires a new isolated pass; this builder record supplies
test and command evidence only. Keep the first review intact. No independent
verdict is inferred from passing tests or copied from AR-138.
