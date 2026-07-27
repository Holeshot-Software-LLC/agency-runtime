---
title: "Worklog detail: ci: run exhaustive Python verification on demand"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [ci, testing, coverage, cost]
related:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
supersedes: []
superseded_by: null
type: worklog
commit: 60543e1
short: 60543e1
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
---

# Worklog detail: ci: run exhaustive Python verification on demand

## Purpose

Stop routine pull requests and pushes from allocating the exhaustive Python
coverage and six-version compatibility runners while retaining meaningful fast
automatic product evidence.

## Approach

Coverage and compatibility keep their exact commands, isolation, and thresholds
but run only on explicit `workflow_dispatch`. The stable aggregate requires
those jobs to be skipped on automatic events and successful on manual events.
An 18-file production/security spine remains automatic alongside UI coverage,
performance, portability, artifacts, and security.

## Challenges encountered

The previous release-document contract embedded the monolithic local coverage
command. Its test was moved to the manual CI controller contract so the release
modules remain covered without directing routine 69-minute local runs.

## Decisions and alternatives

ADR-0101 records the owner's explicit cost-versus-automatic-exhaustive-evidence
decision. Uninstrumented automatic shards were rejected because they would
retain the same material runner envelopes.

## Verification

- The production/security spine passed 521 tests with 5 platform skips in
  65.03 seconds.
- Workflow and controller contracts passed 145 tests; the final focused
  release-packaging contract passed 120 tests in 15.28 seconds.
- Ruff lint and format, Markdown metadata, policy availability, worklog
  currentness, documentation validation across 440 files, and diff checks
  passed.
- Hosted timing and billing were not claimed; Actions currently rejects runner
  allocation before execution.

## Follow-ups

AR-177 retains the current exact-candidate manual dispatch and hosted topology
measurement as release gates after Actions billing is repaired.
