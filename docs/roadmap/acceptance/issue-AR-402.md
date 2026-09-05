---
title: "AR-402 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, staffing]
related:
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/roadmap/handoffs/issue-AR-400.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-402
candidate_commit: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/667
---

# AR-402 acceptance verification record

Candidate is the implementation merged through PR #669. Builder rows identify
observable artifacts; the isolated verifier alone supplies judgments.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Shipped roster accepts a backend implementer across all five hosts without domain requirements` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:23-57` |
| 1 | test | `One indivisible multi-domain unit selects only its faithful nominee, not extra domain-covering workers` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:60-126` |
| 1 | file | `Domain overlap contributes recall evidence without acting as a typed safety predicate` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:2110-2168` |
| 1 | file | `Recruiter sees unit and candidate domains as evidence` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:2260-2310` |
| 2 | test | `Packaged backend planners retain plan authority and are rejected for modification` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:23-57` |
| 2 | test | `Explicit out-of-scope exclusions still reject a candidate` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:129-135` |
| 3 | test | `Actual seeded audited roster and host safety context, not an upgraded fabricated contract` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:23-57` |
| 3 | test | `Backend, frontend, operations and review nominees pass full proposal verification` | 2026-09-05 | `tests/test_subject_domain_eligibility.py:60-126` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-402.1-20260905-32019fe1` | `40be5ba2412add645424ffe27aca4758fd845e5087c572bb81769dd3229c2f67` | 2026-09-05 | tests/test_subject_domain_eligibility.py:23-126 asserts eligibility without domain requirements and single-member selection; inference.py:2110-2168 and 2260-2310 retain domains in recall evidence and recruiter inputs. |
| 2 | satisfied | `AR-402.2-20260905-f90310bc` | `bf13a138e3cbe988ce3f2b8784c8bbb84c51cf3bd4da780c57938b1dfbb43c3b` | 2026-09-05 | tests/test_subject_domain_eligibility.py:23-57 verifies packaged planners retain plan authority and reject implementation across five hosts, while lines 129-135 verify explicit out-of-scope rejection. |
| 3 | satisfied | `AR-402.3-20260905-d83f3224` | `c8df77df252c61664b00e4215ca1573a6a194e6472994a0a64b6eb9683943eb3` | 2026-09-05 | tests/test_subject_domain_eligibility.py:23-126 uses the seeded packaged roster without contract authority changes and verifies accepted backend, frontend, operations and review nominees through full proposal verification. |

## Builder notes

Tests use deterministic provider replies; they are not live staffing claims.
AR-400 separately owns installation and all-host smoke evidence.

