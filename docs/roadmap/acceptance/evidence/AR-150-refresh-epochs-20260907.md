---
title: "AR-150 current refresh epoch evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, concurrency, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-150 current refresh epoch evidence

## Source and scope

Review checkpoint 4f3d22fac289f2794e54bea9f95c9500752f06ba, product source
cd0616686d462a1c21bad7feedc2fe91db9f350d. The review adds records only.
The original shared-epoch implementation at 6a3bdaa is present, with AR-138's
cd35aa2c protection for late errors as well as successes.

`git diff --exit-code 2ecde1a5 HEAD -- agency_runtime tests scripts`
returned zero with no output at the review checkpoint. Product, test and browser
checker bytes match the repaired, accepted AR-138 candidate. No new runtime,
test, polling policy, provider or authentication changes are made here.

## Commit ownership

`agency_runtime/dashboard/dashboard-live.js:951-1012` binds view work to a
shared commit generation and the exact scope controller. Starting view intent
cancels full/control requests and invalidates older view scopes. Finishing an
obsolete request cannot clear the current request; control polling resumes only
when the active view requests have completed.

`dashboard-live.js:2076-2195` prevents a control poll from starting across
active full/view work. Control/full results check request generation, controller
identity and shared commit generation before any state application. Starting a
full refresh cancels older view scopes first. Success and error paths both
reject obsolete requests.

`dashboard-live.js:2353-2387` applies the same ownership test to workforce
refresh, including caller-supplied abort signals. Cancellation does not publish
a stale worker snapshot as current.

Existing executable deferred-response cases include:

- `tests/dashboard_ui.test.mjs:4636-4729`: newer roster intent wins pending
  control and full refreshes; the obsolete live revision is not applied.
- `tests/dashboard_ui.test.mjs:4730-4784`: cross-view invalidation aborts
  pending remediation without overwriting its last good data or leaving busy UI.
- `tests/dashboard_ui.test.mjs:6538-6609`: both exact-first and
  operational-first completion order retain the newest compatible roster state.
- `tests/dashboard_ui.test.mjs:7953-8036`: obsolete network/401/503 errors
  cannot overwrite newer success, across control/full/live/reconciliation paths.

## Current verification

Fresh source-only Node coverage run, September 7: **172 passed**, no fail/skip,
227.66ms. All seven current production JavaScript modules remain in scope.

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Measured lines/branches/functions: **96.93/86.58/95.71**. The current floors and
production-only denominator are governed by ADR-0220. This does not claim the
superseded mixed-denominator 95/90/96 command passes.

Fresh warning-strict server integration run, with `PYTHONPATH=.`:
**180 passed in 28.82s**, no skips/failures.

```bash
python -m pytest tests/test_dashboard.py \
  tests/test_dashboard_auth_boundary_regression.py \
  tests/test_dashboard_transaction_refactors.py -q -W error
```

The prior named spine (1085 pass/three existing skips), routing and 184/184
decision-conformance receipts are reused with unchanged source/test identity,
not represented as new runs. No exhaustive corpus, interpreter matrix or
hosted workflow dispatch was run for this package.

## Unchanged installed-wheel evidence

The existing [repaired AR-138 receipt](AR-138-repaired-dashboard-20260907.md#browser-evidence)
covers the exact same ten dashboard asset bytes and unchanged Python server.
Its rebuilt wheel hash is
`45b38a0873bb7730213bf587970782f5c130ff81394f7e1d85a73aded4db5db3`.
The authoritative complete wheel hash and report hash are in that linked receipt;
the raw JSON and three screenshots remain immutable at 2ecde1a5.

At 05:15:13Z, the wheel passed 21 loaded views at 1280/1024/375 px. Real control
polling preserved focus, selection and open disclosures. Injected control failure
retained last-good revision with a visible stale indicator and safe correlated
ID, then recovered. This is reused same-byte evidence, not a new installed run.
It is neither native-host activation nor full WCAG/screen-reader certification.

## Acceptance boundary

These are builder evidence citations, not acceptance judgments. The four
original AR-150 criteria require their own isolated verdicts before done.
AR-138's accepted status alone is not substituted for that review.
