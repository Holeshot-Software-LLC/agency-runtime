---
title: Preserve preflight lease margin and hosted platform coverage
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [preflight, portability, testing, ci, reliability]
related:
  - docs/roadmap/issue-AR-109-hosted-process-security-test-fidelity.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4dccae796fbf269c1df8bad3538b5260e7047636
short: 4dccae7
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-109-hosted-process-security-test-fidelity.md
---

# Worklog detail: Preserve preflight lease margin and hosted platform coverage

## Purpose

Close the remaining PR #111 hosted-gate gaps without excluding production code
from coverage or weakening the preflight lease guarantee under host load.

## Approach

Every preflight transition that creates or recovers a lease now writes its
activity timestamp from the same SQLite clock sample used to calculate lease
expiry. Portable contract doubles exercise the Win32 native-binding,
descriptor, timestamp, containment-cleanup, and artifact-verifier branches that
Linux coverage legitimately counts.

## Challenges encountered

The hosted Linux gate passed 6,886 tests but exposed 29 platform-specific
statements that local Windows coverage had executed. Separately, Windows Python
3.14 observed a 15-millisecond delay between two database clock evaluations,
which consumed part of the configured five-second lease safety margin.

## Decisions and alternatives

The 100% line-and-branch gate remains unchanged. Excluding Windows production
code from Linux measurement and increasing timing tolerance were rejected
because both would hide portable contract gaps. One database clock sample gives
the lease and activity fields an exact, load-independent relationship.

## Verification

- Exact new regression set: 7/7 passed warning-strict on Windows.
- Full affected files on Windows Python 3.14: 395/395 passed warning-strict.
- Native Linux portable-contract slice: 4/4 passed warning-strict.
- Native Linux coverage no longer reports any of the hosted missing lines.
- Ruff, formatting, documentation, tracker mapping, and whitespace gates passed.

## Follow-ups

Require the complete hosted matrix to pass before marking
[AR-109](../roadmap/issue-AR-109-hosted-process-security-test-fidelity.md) done
or merging PR #111.
