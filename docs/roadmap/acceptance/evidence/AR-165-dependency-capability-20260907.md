---
title: "AR-165 strict dependency-review capability evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [security, ci, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/acceptance/issue-AR-165.md
  - docs/decisions/0228-reconcile-dependency-review-evidence-gates.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-165 strict dependency-review capability evidence

## Reproduction and repair

Baseline main ba6e55cb7013acec6589a30e77b674a86ecf0cf3, clean merge ledger
220c0776e47c7b51d19010e2fd6ebdb92fd195a5. The actual embedded classifier was
executed through the existing test helper in fresh temporary directories,
without network calls. Four independent baseline cases returned exit zero:

| Input | Baseline emitted classification | Repaired result |
|---|---|---|
| HTTP 403 comparison with first message rate-limit, duplicate last message Forbidden and the exact remaining tuple | available=false, http_status=403, reason=private_or_internal_repository_dependency_review_unavailable | exit 1; no outputs or stdout |
| Repository identity with first full_name wrong/repository and duplicate final expected name, followed by exact comparison 403 | available=false, http_status=403, same unavailable reason | exit 1; no outputs or stdout |
| HTTP 200 comparison object with message not a diff | available=true, http_status=200, reason=repository_dependency_review_available | exit 1; no outputs or stdout |
| HTTP 200 array containing a NaN metadata value | available=true, http_status=200, same available reason | exit 1; no outputs or stdout |

The exact duplicate specimens now appear in the new parameterized tests.
Baseline and repaired commands used the same helper and inputs; return codes,
output dictionaries and bounded stderr were read back. Repaired parser failures
emit only the fixed response field name and a bounded invalid-JSON diagnostic;
the object-shape case emits the fixed malformed-success diagnostic.

Both response readers now enforce strict UTF-8 JSON without duplicate keys or
NaN/Infinity constants, reject excess nesting without a traceback, and read at
most 1 MiB plus one byte before enforcing the 1 MiB limit again. The growth
test executes the actual reader definitions with a file reporting size one but
a larger stream: exactly 1048577 bytes are requested and the payload is rejected.
Existing regular-file/link-count checks remain. This is a bounded read, not a
new claim of same-account race-proof filesystem brokering.

HTTP 200 requires an array of objects, matching the endpoint's response shape;
full dependency business-field validation remains the native action's job.
Valid empty, single-change and multi-change arrays still select that action.
The recognized 403 tuple, private/internal non-fork identity policy, authenticated
requests, action pins, audit installation and aggregate are unchanged.

## Unchanged native path

The parsed baseline workflow at 220c0776e47c7b51d19010e2fd6ebdb92fd195a5
was compared step-by-step with the repaired working tree (strict equal-length
zip, identifying changes by step ID). Actual retained output:

```json
{"baseline":"220c0776e47c7b51d19010e2fd6ebdb92fd195a5","changed_step_ids":["dependency-review-capability"],"native_action":"actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294","native_inputs":{"fail-on-severity":"moderate","retry-on-snapshot-warnings":true},"non_classifier_steps_identical":true}
```

Read authority remains the authenticated HTTP-200 exact repository identity,
with the workflow's contents-read permission. Commit 55a00db2 deliberately
removed the optional `permissions.pull` projection requirement; its positive
regression remains. An absent optional projection is not an authority mismatch.

## Fresh verification

Python 3.12.3, Linux, checkout-local imports:

```bash
PYTHONPATH=. python -m pytest tests/test_release_packaging.py -q -W error -k dependency_review
PYTHONPATH=. python -c 'import pytest; from scripts.run_local_gates import WORKFLOW_CONTRACTS; raise SystemExit(pytest.main([*WORKFLOW_CONTRACTS,"-q","-W","error","-k","not windows"]))'
PYTHONPATH=. python -c 'import pytest; from scripts.run_local_gates import PRODUCTION_SPINE; raise SystemExit(pytest.main([*PRODUCTION_SPINE,"-q","-W","error"]))'
```

- Focus: 62 passed/128 deselected, 1.43s, no skips/failures.
- Full governed workflow package: 235 passed/five Windows-named deselections,
  6.62s, no skips/failures.
- Fresh named production spine: 1085 passed/three existing skips, 70.97s.
- Ruff check and format: 766 files pass. Scoped diff check returns zero.

The 25 new cases include valid arrays, duplicate identity/error fields,
non-finite constants, non-array/non-object success, deep nesting, both response
files missing/empty/oversized/non-file/invalid-UTF-8, and bounded growth reads.
No new skip, xfail, suppression or threshold change. Source changes only in
dependency-review.yml and its test module. No Python runtime/script change.

Unchanged AR-163 DOM 188-pass receipt and same-byte AR-156 loaded-browser
evidence are reused explicitly; neither was rerun for this workflow-only change.
No exhaustive corpus, coverage/matrix dispatch, Windows execution or native-host
activation claim.

## Current capability and hosted limits

Read-only authenticated commands on September 7, with no headers or tokens kept:

```bash
gh api repos/Holeshot-Software-LLC/agency-runtime --jq '{full_name,visibility,fork,permissions:{pull:.permissions.pull}}'
gh api 'repos/Holeshot-Software-LLC/agency-runtime/dependency-graph/compare/6d1ca01fb572e58bc5b1186bc9114ae0b7a789ba...ba6e55cb7013acec6589a30e77b674a86ecf0cf3' --jq '{response_type:type,entries:length}'
```

Both commands return zero. Actual retained projections:

```json
{"fork":false,"full_name":"Holeshot-Software-LLC/agency-runtime","permissions":{"pull":true},"visibility":"public"}
{"entries":0,"response_type":"array"}
```

This proves comparison access only for that calling identity/revision pair.
It is not current hosted native-action execution or workflow-token authority.
The historical private-repository/billing narrative is not a fresh diagnosis.
AR-159 retains hosted check and enforcement proof.

GitHub's [official dependency-review endpoint documentation](https://docs.github.com/en/rest/dependency-graph/dependency-review?apiVersion=2022-11-28)
describes an array response, contents-read permission for fine-grained tokens,
and the private-unlicensed/fork 403 boundary. The repair retains the existing
exact response policy rather than broadening that fallback.

## Reconciled measurement and tracker requirements

ADR-0228 explicitly revises only 8 and 9 before review. No speed or billing
savings claim is made; any future claim still needs a matched hosted run with
selected path, stable check name and raw duration. Historical 0.43 runner-minutes
is not a comparison or rounded billing result. AR-165 is in pre-tracker-history;
AR-347's existing exemption applies, not a newly waived remote parity failure.
Both original criteria remain in the canonical record. Criteria 1–7 are unchanged.

## Publication validation

Fresh September 7 publication checks all return zero:

- Metadata: 1185 Markdown documents checked.
- Policy availability: current.
- Exact worklog: 1981 substantive commits indexed before this repair commit.
- Strict docs with required trackers: 1185 Markdown files pass.
- Strict tracker: 397 mapped records pass; two historical PR-tracked items skipped.
- Ruff check/format: 766 files pass; scoped diff check passes.

AR-165 remains explicitly exempt and unmapped, not remotely closed. These are
repository validation results, not builder acceptance verdicts.
