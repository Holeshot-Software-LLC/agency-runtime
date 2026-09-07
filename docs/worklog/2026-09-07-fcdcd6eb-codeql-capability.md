---
title: "Validate bounded CodeQL capability responses"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [ci, security, evidence, backlog]
related:
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fcdcd6ebee6b522281d23a49d2bdc5f95c6649f9
short: fcdcd6eb
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
---

# Worklog detail: Bounded CodeQL capability

## Approach and challenges

The fan-out redesign already exists. The actual baseline shell falsely publishes
available=true for HTTP 200 with no response body. Bound transfer and reads,
strictly parse JSON, check visibility and alert-array shape, and publish outputs
only after classification. Preserve exact normalized unavailable messages and
safe status-only errors. The same shell reproduction now fails without outputs.

The focused test expansion initially had 64 passes and one failure with an
unbounded payload-derived case ID. Bounded descriptive parameter IDs corrected
the harness; no production suppression or skipped regression was introduced.

## Decision

ADR-0226 changes only criterion 8: current capability/evidence limits must be
reported and any savings claim still needs matched hosted measurement. The repo
now reports public with a successful code-scanning read for the calling identity;
that is not workflow-token or hosted analysis proof. Preserve original wording
and telemetry; no claimed benchmark pass. The other eight criteria stay unchanged.
AR-159 continues to own hosted enforcement. No settings/licensing/dispatch change.

## Verification

CodeQL focus 65 pass/100 deselected (1.48s); final workflow five-module package
210 pass/five Windows-named deselections (5.87s), warning-strict. Fresh named
spine 1085 pass/three existing skips (68.09s). Ruff check/format pass, 766 files.
Metadata/policy, strict docs/tracker, exact worklog and diff checks pass.
No Python runtime or script changes; UI/browser receipts reused explicitly.
Windows, hosted analyzer execution and exhaustive diagnostics are not claimed.

## Follow-ups

Freeze nine builder rowsets at fcdcd6eb and require isolated acceptance before
completion. Current count remains 40 actual trackers plus 89 unfinished legacy
records. Publish one normal PR after acceptance, then the next oldest record.

## Frozen review

b3293188 freezes nine builder rowsets at fcdcd6eb, adds the exact implementation
citation to ADR-0226 and advances the active capsule. Metadata and strict docs
validation pass for 1173 Markdown files. The next step is isolated acceptance;
no builder-assigned verdict or completion is recorded.
