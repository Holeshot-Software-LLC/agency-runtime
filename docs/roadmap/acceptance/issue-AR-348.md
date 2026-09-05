---
title: "AR-348 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, hiring]
related:
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md
  - docs/decisions/0221-enforce-hiring-independence-on-resolved-provider-chains.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-348
candidate_commit: c9b678a57bf3626b816cfe368de74001292ec0da
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/406
---

# AR-348 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `Configured overlap uses every pair of adapter/model entries rather than profile names or primary-only comparison` | 2026-09-05 | `agency_runtime/core/inference_profiles.py:281-298` |
| 1 | file | `Central enforcer compares resolved chains and raises the existing route-named ConfigValidationError in strict mode` | 2026-09-05 | `agency_runtime/core/inference_profiles.py:378-415` |
| 1 | file | `Hiring preflight and actual reviewer resolver supply authoritative stage chains to the enforcer` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:1291-1330` |
| 1 | file | `Public hiring checks initial pairs before creator invocation; actual critic resolution uses the same boundary` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:2400-2485` |
| 1 | file | `Security review checks its resolved chain and the caller-supplied creator before invoking` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:1372-1440` |
| 1 | test | `Public-path matrix covers profiles, defaults, harness/env override, legacy and fallback chains; strict negatives require config error, zero calls, no case and no enabled worker` | 2026-09-05 | `tests/test_workforce_dynamic_hiring.py:507-617` |
| 1 | test | `Safety-repair primary/fallback overlap checks its own creator and avoids the replacement call; invocation tests recheck changed routes` | 2026-09-05 | `tests/test_workforce_dynamic_hiring.py:651-731` |
| 1 | command-output | `Focused five-file production-path package passes 413 tests with one existing skip; original negative run retained` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md#focused-verification` |
| 2 | file | `Strict=false exits the enforcer without blocking; configured adapter/model comparison remains the same warning criterion` | 2026-09-05 | `agency_runtime/core/inference_profiles.py:378-415` |
| 2 | file | `Warning identity compares the same normalized adapter and exact model values across both chains` | 2026-09-05 | `agency_runtime/core/inference_profiles.py:281-298` |
| 2 | file | `Security review continues to combine deterministic overlap and reviewer-provided warning when returning the verdict` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:1390-1440` |
| 2 | test | `Non-strict matrix requires actual successful hiring, three provider calls, exact stored security warning and enabled roster entry` | 2026-09-05 | `tests/test_workforce_dynamic_hiring.py:535-617` |
| 2 | test | `Non-strict safety repair remains successful with five calls and its stored overlap warning; distinct strict chains also remain allowed` | 2026-09-05 | `tests/test_workforce_dynamic_hiring.py:619-699` |
| 2 | command-output | `The complete focused suite passes, including the warning-only and distinct-provider controls` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md#focused-verification` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
