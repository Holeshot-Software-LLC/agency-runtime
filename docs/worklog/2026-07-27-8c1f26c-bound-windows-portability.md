---
title: "Worklog: Bound automatic Windows portability"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [ci, github-actions, cost, windows, testing]
related:
  - docs/roadmap/issue-AR-180-bound-automatic-windows-portability-fanout.md
  - docs/decisions/0104-bound-automatic-windows-portability.md
supersedes: []
superseded_by: null
type: worklog
commit: 8c1f26c
short: 8c1f26c
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-180-bound-automatic-windows-portability-fanout.md
---

# Worklog detail: Bound automatic Windows portability

## Purpose

Reduce the highest-cost routine GitHub Actions fan-out without removing real
Windows feedback or weakening the explicit release compatibility gate.

## Approach

The automatic `windows-portability-contract` matrix now contains only Python
3.13. Its prerequisite, commands, Windows 2022 runner, timeout, stable job ID,
and fail-closed aggregate requirement are unchanged. The separately governed
manual compatibility graph still runs the complete corpus on Windows Python
3.10 and 3.14. A workflow contract test pins the one-cell automatic matrix.

AR-180 and ADR-0104 record the scope and cost-versus-coverage decision, and the
linked tracker issue is [#155](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/155).

## Challenges encountered

The strict tracker validators still report the pre-existing AR-128 through
AR-177 roadmap items whose tracker URLs were already pending authorization.
The ordinary documentation validator passes all 450 maintained Markdown files,
and AR-180 itself has a live tracker URL and matching `epic:testing` label.

## Decisions and alternatives

[ADR-0104](../decisions/0104-bound-automatic-windows-portability.md) retains one
automatic current-interpreter Windows signal and preserves manual supported-
version boundary proof. Making Windows entirely manual and retaining all three
automatic cells were both rejected.

## Verification

- `tests/test_release_packaging.py`: 120 passed warning-strict.
- Fast Python production spine: 521 passed, 5 platform skips warning-strict.
- Dashboard UI suite: 105 passed.
- Deterministic routing evaluation: all gates passed.
- Ruff check and format check passed across 580 files.
- Metadata, policy-availability, worklog-current, documentation, and whitespace
  checks passed.
- Strict tracker parity was attempted and failed only on the repository's
  pre-existing AR-128 through AR-177 missing remote records.

## Follow-ups

Run one hosted code pull request after the organization billing or spending
state accepts Actions jobs, then attach its runner topology and billed-minute
evidence to AR-180 before calling the projected reduction measured savings.
