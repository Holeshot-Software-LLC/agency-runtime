---
title: "AR-304: Preserve recruiter and critic validation diagnostics"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [workforce, inference, observability, security, diagnostics]
related:
  - docs/roadmap/issue-AR-276-preserve-planner-repair-diagnostics.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-303-bound-full-roster-embedding-requests.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/preflight_failure.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-304
priority: p0
tracker_url: null
depends_on: [AR-276]
blocks: [AR-297]
---

# AR-304: Preserve recruiter and critic validation diagnostics

## Problem

AR-297 live attempts collapsed all malformed recruiter candidate rows to
`invalid_candidate` and all strict critic contract failures to a generic
provider rejection. The content-free receipt therefore could not distinguish
an unknown ID, invalid score, malformed evidence, conflicting classification,
or invalid critic veto. Repeating the same model call could not be justified
from durable evidence.

## Current state

- The candidate implementation assigns one closed runtime-owned subreason to
  every invalid recruiter candidate row and supplies it to the bounded repair
  prompt.
- Strict critic responses now require the exact two-field shape, one Boolean
  approval, at most 16 unique hyphenated codes, no reasons on approval, and at
  least one reason on rejection.
- Only closed allowlisted codes cross the preflight failure boundary. Provider
  prose, unknown codes, candidate IDs, scores, and evidence text are not
  retained.
- The first private AR-297 preflight persisted two exact
  `recruiter_candidate_score_invalid` diagnoses. That attempt also proved the
  prior embedding scalar failure had moved to the provider boundary.
- Focused warning-strict coverage currently passes 129 tests, including every
  recruiter subreason and adversarial provider-authored critic text.
- Tracker creation is prohibited by the active task.

## Approach

Classify rejected candidate rows in a stable deterministic order using only
the schema and governed roster. Keep the broad existing repair/failure codes
for compatibility, and add a closed subreason solely when that broad code is
`invalid_candidate`.

Validate critic semantics before accepting its approval or veto. Project only
stage-correct allowlisted reason codes into durable preflight receipts. Invalid
provider-authored values may cause one bounded semantic repair but may never
become durable content.

## Dependencies

- AR-276 supplies the bounded planner diagnostic projection pattern.
- Existing recruiter and critic repair budgets remain authoritative.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] Every recruiter candidate-row validation branch has one closed subreason.
- [x] Strict critic approval and rejection semantics fail closed with bounded
      stage-specific codes.
- [x] Repair prompts receive only runtime-owned diagnostic tokens.
- [x] Preflight receipts preserve valid recruiter/critic codes and drop unknown
      or provider-authored values.
- [x] Focused warning-strict tests and Ruff checks pass.
- [x] One private live failure persists a precise recruiter subreason without
      provider content.
- [ ] The named repository gates pass on the checkpointed implementation.
- [ ] A same-repository tracker is created and linked after explicit
      authorization.
