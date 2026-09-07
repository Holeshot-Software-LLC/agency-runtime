---
title: "AR-162 bounded CodeQL capability evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, ci, security, cost, backlog]
related:
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/codeql.yml
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-162: Bounded CodeQL capability evidence

## Baseline and repair

Baseline main f18b5acf, publication ledger f0fc06de. The one-preflight,
conditional-language-matrix and stable-result redesign already exists.
The whole baseline shell probe was executed locally with curl replaced by a
function returning HTTP 200 without creating a response body. It exited zero
and published available=true, repository_code_scanning_available, HTTP 200 and
public visibility; the response file did not exist. No actual network call or
CodeQL initialization occurred in this controlled reproduction.

The repaired whole shell returns one, empty stdout and a bounded invalid-JSON
diagnostic for the identical missing-body scenario. No availability is published.

The single request keeps its existing 10-second connect and 30-second total
timeouts and adds a 1 MiB transfer bound. Classification independently enforces
a bounded, non-linked regular response file and bounded UTF-8 JSON read.
Missing, empty, invalid UTF-8/JSON, duplicate-key, non-finite-number, excess-depth,
oversized and wrong-shaped success data fail before output publication.
Available responses must be a per-page-one array of alert objects. This checks
the array/object shape, not every alert business field. The existing exact
normalized private/internal missing-entitlement messages are the only unavailable
path. Unknown status/visibility, ambiguous 403 and public entitlement claims fail.

GitHub's [code-scanning endpoint documentation](https://docs.github.com/en/rest/code-scanning/code-scanning?apiVersion=2022-11-28#list-code-scanning-alerts-for-a-repository)
documents the alert-array response and per-page bound. No alert contents are
needed or published in this receipt.

## Preserved workflow contract

The workflow still has capability, analyze and codeql jobs. Every configured
event reaches one capability curl request, with no preflight checkout or
language fan-out. Only available=true permits the exact Python and
JavaScript/TypeScript analyses. Existing immutable checkout/CodeQL pins,
security-extended queries, per-language categories and SARIF upload remain.

Only analyze has security-events:write; capability has contents/code-scanning
read access and the stable CodeQL result aggregate has contents read only.
Unavailable capability writes both language records with analysis_performed=false
to one artifact, initializes no CodeQL action and deliberately skips analyze.
The aggregate rejects missing/failed/cancelled/malformed/inconsistent prerequisites.
Push, PR, weekly cron, manual dispatch and concurrency remain unchanged.

## Fresh verification

Focused execution of tests/test_release_packaging.py with -q -W error -k codeql:
65 pass, 100 deselected, no skips/failures, 1.48s. Forty-five new classifier cases
cover bounded success, exact unavailable messages and adversarial bodies/states.
Test payloads have bounded descriptive IDs, including the 1 MiB boundary case.

Final fast workflow command in the development environment, worktree imports first:

    PYTHONPATH=. python -c 'import pytest; from scripts.run_local_gates import WORKFLOW_CONTRACTS; raise SystemExit(pytest.main([*WORKFLOW_CONTRACTS, "-q", "-W", "error", "-k", "not windows"]))'

Result: 210 pass, five Windows-named deselections, no skips/failures, 5.87s.
This includes the final status-only diagnostic assertion added after the
65-case focused run. All five governed workflow modules are exercised.

Fresh named production spine:

    PYTHONPATH=. python -c 'import pytest; from scripts.run_local_gates import PRODUCTION_SPINE; raise SystemExit(pytest.main([*PRODUCTION_SPINE, "-q", "-W", "error"]))'

Result: 1085 pass, three existing skips, 68.09s. No runtime or named-spine file
was changed. Ruff check/format pass, 766 files; diff whitespace passes.
The existing UI 188/current-floor and 21 loaded-browser receipts remain
unchanged-input reuse. No new exhaustive suite, Windows run or live host claim.

## Current capability and hosted limits

September 7 authenticated read-only API calls:
GET repository identity reports full_name Holeshot-Software-LLC/agency-runtime,
visibility public, fork false and default_branch main. GET
code-scanning/alerts?per_page=1 returns HTTP 200, response_type array, entries 1.
Only identity and response shape/count were reported; no alert data was retained.
This proves availability for the calling identity, not the workflow token,
the current source's security status or a successful hosted analyzer run.

AR-159's separate receipt records active workflows, empty current-main checks,
old August 31 cancelled CI/repository-CodeQL runs and a separate active dynamic
CodeQL workflow. The generated workflow's identity remains relevant to AR-159's
check binding. None of those facts is a current hosted pass or billing diagnosis.
No settings, permission, subscription, analyzer execution or dispatch was changed.

## Measurement boundary

ADR-0226 explicitly revises only criterion 8. No current speed or billing savings
are asserted, no raw job count is converted to billed minutes, and no historical
measurement is promoted to this candidate. A future savings claim still requires
a matched unavailable-path topology and raw-duration measurement. The original
criterion and 0.34/0.24 raw-minute history remain in the canonical issue.
The other eight criteria are unchanged. AR-159 remains open for current hosted
check identities and enforced protection.

## Tracker history

AR-162 is listed in docs/roadmap/pre-tracker-history.txt and retains tracker_url
null; no tracker creation or duplicate issue occurs. Strict tracker parity is
the applicable existing-exemption check, not a claim that a new issue was filed.
Before accepted completion, counts remain 40 actual open trackers plus 89
unfinished legacy records, 129 local unfinished. Candidate-bound isolated
verification is still required; this builder receipt does not assign verdicts.
