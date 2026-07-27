---
title: "AR-180: Bound automatic Windows portability fan-out"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [ci, github-actions, cost, windows, testing]
related:
  - docs/decisions/0104-bound-automatic-windows-portability.md
  - .github/workflows/ci.yml
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-180
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/155
depends_on: []
blocks: []
---

# AR-180: Bound automatic Windows portability fan-out

## Problem

Every automatic code pull request and push allocated three paid Windows runners
to execute the same focused portability contract on Python 3.11, 3.12, and
3.13. The organization billing audit found Windows runner time to be the
largest Actions cost class, and this repository produced almost all of the
organization's Actions spend.

## Current state

Automatic code events retain one Windows 2022 portability job on Python 3.13.
The explicit manual compatibility gate remains unchanged and continues to run
the complete serial corpus at the supported Windows boundaries, Python 3.10
and 3.14. The aggregate still requires the automatic portability job to
succeed; neither a skipped nor a missing result can pass.

## Approach

Keep the focused atomic-process and canonical-archive portability contract on
the current CI interpreter for every code change. Use the already-governed
manual compatibility workflow for exhaustive Windows version-boundary proof.
Pin the one-cell automatic matrix in the workflow contract test so routine
fan-out cannot grow again without an explicit contract change.

## Dependencies

ADR-0104 owns the cost-versus-automatic-version-coverage decision. Hosted
measurement depends on the external organization Actions billing or spending
state accepting runner allocation again.

## Acceptance

- [x] Automatic code events allocate one Windows portability runner, not three.
- [x] Manual Windows Python 3.10 and 3.14 compatibility sessions are unchanged.
- [x] The aggregate still requires successful portability evidence.
- [x] Workflow contract tests pin the one-cell Python 3.13 matrix.
- [ ] One hosted code pull request measures the resulting runner topology and
  cost after organization Actions billing is restored.

## Implementation evidence

The automatic primary CI topology drops from ten allocated jobs to eight by
removing the redundant Python 3.11 and 3.12 Windows portability cells. This is
a structural two-runner reduction, not a measured duration or dollar saving.
The manual three-job compatibility matrix and its Windows Python 3.10 and 3.14
pair remain byte-for-byte unchanged.
