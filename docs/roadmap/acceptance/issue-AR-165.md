---
title: "AR-165 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, security, ci]
related:
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md
  - docs/decisions/0228-reconcile-dependency-review-evidence-gates.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-165
candidate_commit: 9effff3f6c4f4fbe59de8793df074a041e64dab9
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-165 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | One stable job with contents-read authority and nonpersistent checkout credentials | 2026-09-07 | .github/workflows/dependency-review.yml:1-24 |
| 1 | test | Executable workflow contract asserts the job count, name and permissions | 2026-09-07 | tests/test_release_packaging.py:1148-1165 |
| 1 | command-output | All 62 focused cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#fresh-verification |
| 2 | file | Two authenticated bounded requests write runner-owned files and handle curl failures before emitting bounded metadata | 2026-09-07 | .github/workflows/dependency-review.yml:24-63 |
| 2 | test | Exact request bounds, credentials, failure branches and output field list are asserted | 2026-09-07 | tests/test_release_packaging.py:1168-1196 |
| 2 | file | File validation and bounded read reject malformed UTF-8 JSON with fixed diagnostics | 2026-09-07 | .github/workflows/dependency-review.yml:90-122 |
| 2 | test | Both response-file boundaries and post-stat growth exercise the actual reader | 2026-09-07 | tests/test_release_packaging.py:1496-1556 |
| 3 | file | Array-of-objects HTTP-200 response selects native availability | 2026-09-07 | .github/workflows/dependency-review.yml:124-152 |
| 3 | file | Availability gates the pinned action at moderate severity | 2026-09-07 | .github/workflows/dependency-review.yml:183-189 |
| 3 | test | Empty, single and multiple-change arrays execute the actual classifier successfully | 2026-09-07 | tests/test_release_packaging.py:1277-1320 |
| 3 | command-output | Baseline/current semantic comparison confirms the unchanged action, inputs and all non-classifier steps | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#unchanged-native-path |
| 4 | file | Status, strict payload, authenticated identity and exact scoped forbidden tuple gate classification | 2026-09-07 | .github/workflows/dependency-review.yml:84-169 |
| 4 | test | Ambiguous API status/body and repository identity, authority and scope fail with no outputs | 2026-09-07 | tests/test_release_packaging.py:1323-1385 |
| 4 | test | Missing optional permissions projection is intentionally accepted after exact authenticated identity | 2026-09-07 | tests/test_release_packaging.py:1388-1402 |
| 4 | test | Duplicate fields, non-finite constants, deep nesting and malformed success shape fail without outputs | 2026-09-07 | tests/test_release_packaging.py:1430-1494 |
| 4 | test | Both file boundaries and bounded growth fail closed | 2026-09-07 | tests/test_release_packaging.py:1496-1556 |
| 4 | command-output | Four actual baseline false classifications reject after repair; all focused tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#reproduction-and-repair |
| 5 | file | Fallback notice, runtime installation, audit-tool pin and audit step are explicit | 2026-09-07 | .github/workflows/dependency-review.yml:175-207 |
| 5 | test | Native/fallback wiring and tool pin are asserted | 2026-09-07 | tests/test_release_packaging.py:1199-1273 |
| 5 | command-output | Focused workflow tests pass without changing either installed-runtime or native path | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#fresh-verification |
| 6 | file | Always-run aggregate requires exact coherent outcome maps for each path | 2026-09-07 | .github/workflows/dependency-review.yml:208-268 |
| 6 | test | Actual aggregate accepts both coherent paths and rejects failed, missing and cross-path states | 2026-09-07 | tests/test_release_packaging.py:1558-1599 |
| 6 | command-output | Full focus including aggregate cases passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#fresh-verification |
| 7 | file | Test helper extracts and executes the workflow's real embedded classifier | 2026-09-07 | tests/test_release_packaging.py:170-235 |
| 7 | test | Positive paths and adversarial API/repository cases execute the classifier | 2026-09-07 | tests/test_release_packaging.py:1277-1385 |
| 7 | test | Malformed and duplicate/non-finite payload cases reject | 2026-09-07 | tests/test_release_packaging.py:1405-1494 |
| 7 | test | File and growth boundaries plus both aggregate directions execute | 2026-09-07 | tests/test_release_packaging.py:1496-1599 |
| 7 | command-output | Fresh 62 focused, 235 workflow and 1085/three-existing-skip spine results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#fresh-verification |
| 8 | file | Explicit measurement reconciliation preserves originals and requires matched hosted proof for any savings claim | 2026-09-07 | docs/decisions/0228-reconcile-dependency-review-evidence-gates.md#decision |
| 8 | command-output | Fresh public identity and exact comparison output are retained with calling-identity and hosted limitations | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#current-capability-and-hosted-limits |
| 8 | file | No savings claim is made; historical duration is not a matched comparison | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#reconciled-measurement-and-tracker-requirements |
| 9 | file | AR-165 is explicitly in the pre-tracker allow-list | 2026-09-07 | docs/roadmap/pre-tracker-history.txt:30-44 |
| 9 | file | AR-347 governs both strict gates and removes stale mapped exemptions | 2026-09-07 | docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:113-137 |
| 9 | file | Current issue remains unmapped, with no invented tracker URL | 2026-09-07 | docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md:1-28 |
| 9 | file | Explicit reconciliation retains exact parity for any later authorized mapping | 2026-09-07 | docs/decisions/0228-reconcile-dependency-review-evidence-gates.md#decision |
| 9 | command-output | Fresh strict documentation and tracker checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md#publication-validation |

## Verification

All nine current criteria satisfy at 9effff3f6c4f4fbe59de8793df074a041e64dab9
in the first isolated review. Criteria 1–7 are unchanged; ADR-0228 explicitly
reconciles only 8/9 with both originals retained. No hosted-success claim.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-165.1-20260907-c7c7a831` | `ef0a6ccb812e216459576d07bd3f17639352f160a4c29a6237309beb2aebf279` | 2026-09-07 | The workflow excerpt sets contents: read and names the job dependency review; the cited contract asserts exactly one job, and the fresh-verification artifact records all 62 focused tests passing. |
| 2 | satisfied | `AR-165.2-20260907-0a6aa1c8` | `42031a8149a294156e6be1eb34e244960da60d944ef9b097bc065193cd17c355` | 2026-09-07 | Workflow lines 24-63 show both authenticated requests using runner-temp mktemp files, explicit time and size bounds, curl-failure exits, and outputs limited to file paths and HTTP status codes; tests at lines 1168-1196 assert these properties. |
| 3 | satisfied | `AR-165.3-20260907-50619a6f` | `5c662661d11109df18e30cb67e1f9996f7ace5b374d310588c23a537d83eb3ab` | 2026-09-07 | Workflow lines 124–152 select availability for HTTP-200 comparison arrays, lines 183–189 gate the pinned action with moderate severity, and the retained baseline comparison records unchanged native action and inputs. |
| 4 | satisfied | `AR-165.4-20260907-f58f1147` | `473d4f409e6770f15998d4448af7b35b5934f589f18c90e30a43b4f72f28d183` | 2026-09-07 | dependency-review.yml:84-169 enforces exact repository identity and the private/internal non-fork 403 tuple; tests at 1323-1556 cover rejection of unauthorized, rate-limit, malformed, oversized, public and fork responses, and the cited repair artifact documents authenticated requests. |
| 5 | satisfied | `AR-165.5-20260907-9bac37f4` | `3d4be39665d3eafef9c72660d91a98d3a299301a9891b63a45f0c9169e0c2b65` | 2026-09-07 | dependency-review.yml:175-207 installs the project with dependencies and pip-audit==2.10.1, invokes the runtime audit, and explicitly labels it non-equivalent compensating evidence; tests/test_release_packaging.py:1199-1273 asserts this wiring. |
| 6 | satisfied | `AR-165.6-20260907-ca8f654c` | `7a30b27893f761b4abe8621b26ae8b3618eb3f923ff8f1066b6fb0c7e3589705` | 2026-09-07 | dependency-review.yml:208-268 defines one always() aggregate with exact path-specific outcome maps, rejecting invalid availability and all prerequisite mismatches; tests/test_release_packaging.py:1558-1599 covers coherent and rejected states. |
| 7 | satisfied | `AR-165.7-20260907-c9c4e680` | `ce28165fab21100585f3a81aaf705069bf627800db7947f5998a72188897a474` | 2026-09-07 | tests/test_release_packaging.py:170-235 executes the embedded classifier; lines 1277-1599 cover coherent paths, adversarial API and repository identity, bounded files and growth, and coherent and incoherent aggregate results. |
| 8 | satisfied | `AR-165.8-20260907-76164636` | `11d8409f9313db43dbe52b58b2ad16a91fdf70b720d484ed6bc30f317cb98946` | 2026-09-07 | The AR-165 evidence retains public repository identity and successful comparison output, limits proof to that identity and revision pair, and makes no savings claim; ADR-0228 requires matched hosted runs with selected path, stable check name and raw duration for future claims. |
| 9 | satisfied | `AR-165.9-20260907-f5b0efe2` | `8a87f3caa7ab89db3b173dde9570f605622e78fc1190b5bfaafd30c0660bad2a` | 2026-09-07 | The allow-list includes AR-165, its record has tracker_url: null, publication validation records both strict checks passing, and ADR-0228 requires exemption removal and strict URL/state parity upon later mapping. |
