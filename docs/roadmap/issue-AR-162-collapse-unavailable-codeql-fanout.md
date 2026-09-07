---
title: "AR-162: Collapse unavailable CodeQL fanout"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [testing, security, ci, performance, cost, github-actions]
related:
  - docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/roadmap/acceptance/issue-AR-162.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/codeql.yml
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-162
priority: p1
tracker_url: null
depends_on: []
blocks: [AR-159]
---

# AR-162: Collapse unavailable CodeQL fanout

## Problem

The original CodeQL workflow expanded its language matrix before discovering whether the
repository can use native code scanning. When Code Security is unavailable,
two hosted runners independently check out the same revision, issue the same
entitlement request, record equivalent unavailable evidence, and exit without
performing analysis.

## Current state

The one-preflight/conditional-analysis/stable-aggregate redesign is implemented.
September 7 review found a remaining fail-closed gap: the actual shell probe
accepted HTTP 200 even with no response file, publishing available true.
The repair bounds the response to 1 MiB, rejects missing/non-file/malformed or
duplicate-key JSON, validates the available alert-array shape and preserves
only the exact private/internal unavailable messages. Output is written only
after classification. One request, permissions, triggers and pinned analysis
behavior remain unchanged.

Fresh 65 CodeQL-focused cases and all 210 non-Windows fast workflow cases pass;
the named production spine passes 1085 with three existing skips. The whole
shell missing-body reproduction now exits one without availability output.
Exact evidence is in the [receipt](acceptance/evidence/AR-162-codeql-capability-20260907.md).

Current read-only identity is public/non-fork; code scanning returns HTTP 200
with an alert array for the calling identity. This is not a current workflow-token
or hosted analyzer pass. ADR-0226 explicitly makes only the old eighth measurement
requirement claim-conditional; no speed or billing savings are claimed. Following
the preserved first review, it also explicitly reconciles criterion 9 to AR-347's
existing pre-tracker exemption. Criteria 1–7 remain unchanged; all nine current
criteria require a new candidate-bound isolated review.

First isolated review at fcdcd6eb satisfies criteria 1–6 and 8. Criterion 7 is
absent because the rowset lacks a prior trigger/concurrency comparison; criterion
9 is absent because the old wording requires remote parity rather than the
existing legacy exemption. Preserve this result before a revised evidence or
requirements checkpoint. No implementation defect or completion is inferred.

The correction records identical event/concurrency projections before the
original fan-out change and at fcdcd6eb. It adopts AR-347's existing exemption
explicitly for criterion 9, with strict docs/tracker checks passing. Workflow,
tests, scripts and runtime remain byte-identical to fcdcd6eb; all nine criteria
await the new-candidate review. See the
[record correction](acceptance/evidence/AR-162-record-reconciliation-20260907.md).

## Approach

Run one least-privilege, fail-closed capability preflight before matrix
expansion. When native CodeQL is available, preserve the exact Python and
JavaScript/TypeScript matrix, pinned actions, query suite, categories, and SARIF
upload behavior. When it is unavailable, retain one artifact containing
language-specific evidence that explicitly says analysis was not performed.

Publish one stable aggregate job after the preflight and matrix. It accepts only
the two coherent states: successful preflight plus successful analysis matrix,
or successful unavailable classification plus an intentionally skipped matrix.
Missing, failed, cancelled, malformed, and inconsistent states fail closed.

## Dependencies

ADR-0037 governs layered supply-chain analysis. ADR-0097 governs cost-bounded
CI topology without weakening exact verification. AR-159 will use the stable
aggregate only after current hosted check names and repository protection are
explicitly authorized and verified.

## Acceptance

- [ ] Every workflow event performs exactly one native CodeQL capability request.
- [ ] Public, ambiguous, malformed, unauthorized, and unexpected probe responses
  fail closed; only the recognized private/internal missing-entitlement response
  selects the unavailable path.
- [ ] Available repositories run the exact Python and JavaScript/TypeScript CodeQL
  analyses with the existing pinned actions, `security-extended` queries,
  categories, and SARIF upload behavior.
- [ ] Unavailable repositories initialize no CodeQL action and retain both
  language-specific evidence records with `analysis_performed: false`.
- [ ] Only the analysis job receives `security-events: write`; the preflight has
  read-only code-scanning access and the aggregate has contents read access.
- [ ] One stable aggregate rejects missing, failed, cancelled, malformed,
  unexpectedly skipped, or otherwise inconsistent prerequisite results.
- [ ] Push, pull-request, weekly schedule, manual-dispatch, and concurrency behavior
  remain unchanged.
- [ ] Current hosted capability and check-evidence limits are reported accurately;
  any speed or billing-savings claim requires a matched hosted unavailable-path
  topology and raw-duration measurement, and no such claim is made without it.
- [ ] AR-162 follows the governed pre-tracker exemption while unmapped; both strict
  documentation/tracker checks pass, and any later authorized tracker mapping has
  exact URL/state parity with the local record.

## Measurement requirement reconciliation

ADR-0226 preserves the original eighth criterion here: "A matched hosted
unavailable-path run records the new job topology and raw runner duration before
any speed or billing-savings claim is accepted." No current savings assertion
is made and no unavailable-service scenario is manufactured. AR-159 retains
hosted enforcement and current-check proof.

After first review c456b6bd, ADR-0226 also explicitly reconciles criterion 9 to
the existing AR-347 exemption. Its original wording is preserved here: "The
tracker issue and local roadmap record have exact URL/state parity after tracker
creation is authorized." This is not a claim that old remote-parity evidence
exists. Criteria 1–7 remain unchanged; a before/after comparison supplies the
missing evidence for 7. All nine require a new candidate and new verdicts.

Two original unavailable runs consumed 0.34 raw runner-minutes on a PR and 0.24
on a push, using two language jobs with no analysis. These remain historical
telemetry, not a current comparison or a claim about rounded billing units.

## Implementation evidence

The local workflow now uses one capability job, the unchanged two-language
analysis matrix when available, and one stable `CodeQL result` aggregate. The
unavailable recorder emits both language documents in one artifact and cannot
claim analysis. Focused contract tests execute both coherent aggregate paths,
reject adversarial result combinations, execute and inspect unavailable
evidence, pin event and permission boundaries, and preserve exact analyzer
configuration.

The original prediction of lower raw runtime was unmeasured; no September
speed or billable-minute savings follows from it. Current hosted checks remain
unproven under AR-159, and the old billing explanation is not a fresh diagnosis.
This legacy record retains its pre-tracker exemption; no duplicate tracker is
created. The local implementation is ready for candidate-bound isolated review,
not yet marked done.
