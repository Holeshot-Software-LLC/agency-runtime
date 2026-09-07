---
title: "AR-171 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, privacy, dashboard]
related:
  - docs/roadmap/issue-AR-171-redact-dashboard-lifecycle-reasons.md
  - docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-171
candidate_commit: pending
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-171 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Reduced event SQL excludes evidence and removes reason before returning event metadata | 2026-09-07 | agency_runtime/core/store/workforce.py:1977-2000 |
| 1 | file | Dashboard detail explicitly selects reduced history | 2026-09-07 | agency_runtime/server/dashboard.py:2180-2206 |
| 1 | test | Private event setup includes original reason and large evidence document | 2026-09-07 | tests/test_workforce_lifecycle.py:823-852 |
| 1 | test | Reduced event fields and serialized summary exclude original content | 2026-09-07 | tests/test_workforce_lifecycle.py:865-918 |
| 1 | command-output | Actual full Store/HTTP test stdout passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#store-and-http-transcript |
| 2 | file | Reduced history returns a primitive bool flag and never selects content-derived event hashes | 2026-09-07 | agency_runtime/core/store/workforce.py:1987-2000 |
| 2 | test | Summary omits reason_hash and SHA-256 of the exact private reason | 2026-09-07 | tests/test_workforce_lifecycle.py:883-918 |
| 2 | test | Real owner HTTP operation and reduced readback omit raw reason and its derivative hash | 2026-09-07 | tests/test_dashboard.py:1385-1430 |
| 2 | command-output | Full Store/HTTP suites exercise these assertions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#store-and-http-transcript |
| 3 | file | Store converts reason presence to a boolean | 2026-09-07 | agency_runtime/core/store/workforce.py:1987-2000 |
| 3 | file | Renderer tests primitive true and emits only fixed reason text | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1948-1985 |
| 3 | test | Eight presence values cannot render injected notes, hashes, evidence or IMG nodes | 2026-09-07 | tests/dashboard_ui.test.mjs:1286-1313 |
| 3 | command-output | Exact renderer regression stdout and scope | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#renderer-regression-transcript |
| 4 | file | Full-history mode returns original event fields and decoded evidence | 2026-09-07 | agency_runtime/core/store/workforce.py:1977-1986 |
| 4 | file | Full-history mode is explicit and requires an actual boolean | 2026-09-07 | agency_runtime/core/store/workforce.py:1894-1911 |
| 4 | test | Original private note and large document are inserted in Store | 2026-09-07 | tests/test_workforce_lifecycle.py:823-852 |
| 4 | test | Full projection retains exact reason and governed evidence while reduced mode omits them | 2026-09-07 | tests/test_workforce_lifecycle.py:865-918 |
| 4 | command-output | Complete workforce and dashboard suites pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#store-and-http-transcript |
| 5 | test | Store serialized summary excludes note, note SHA-256 and large private event/outcome sentinels | 2026-09-07 | tests/test_workforce_lifecycle.py:883-918 |
| 5 | test | Real authenticated HTTP lifecycle change/readback proves raw and derivative note absence | 2026-09-07 | tests/test_dashboard.py:1385-1430 |
| 5 | test | Production DOM renderer rejects raw/HTML/hash/evidence sentinel projection for eight flags | 2026-09-07 | tests/dashboard_ui.test.mjs:1286-1313 |
| 5 | command-output | Exact Store/HTTP stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#store-and-http-transcript |
| 5 | command-output | Exact focused renderer stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#renderer-regression-transcript |
| 5 | command-output | Full 194-case UI result and unchanged coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#full-ui-and-coverage-transcript |
| 6 | file | Governing decision explicitly replaces mandatory exhaustive gates with scoped verification | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |
| 6 | command-output | Exact focused Store/HTTP command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#store-and-http-transcript |
| 6 | command-output | Exact full UI command and coverage result | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#full-ui-and-coverage-transcript |
| 6 | command-output | Actual fresh named-spine command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#production-spine-transcript |
| 6 | command-output | Raw metadata/policy/worklog/strict docs/tracker/Ruff/diff checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md#record-checks |

## Verification

Pending isolated checks at the frozen candidate.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
