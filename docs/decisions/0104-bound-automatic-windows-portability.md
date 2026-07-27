---
title: "Bound automatic Windows portability to the current interpreter"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [ci, github-actions, cost, windows, testing]
related:
  - docs/roadmap/issue-AR-180-bound-automatic-windows-portability-fanout.md
  - .github/workflows/ci.yml
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
id: ADR-0104
type: decision
deciders: [maintainers]
---

# ADR-0104: Bound automatic Windows portability to the current interpreter

## Context

The automatic Windows portability contract runs four focused test files that
exercise canonical archives, owned process trees, and atomic Windows process
behavior. Running that same focused contract on Python 3.11, 3.12, and 3.13
allocates three paid Windows runners on every code change. Windows minutes are
the organization's most expensive remaining Actions class.

The explicit manual compatibility workflow already preserves full serial test
sessions on Windows Python 3.10 and 3.14. Those endpoints provide the supported
version-boundary evidence needed for release decisions, while the focused
automatic contract provides fast feedback on the current CI interpreter.

## Decision

Run the automatic focused Windows portability contract only on Python 3.13.
Keep its job ID, Windows 2022 runner, commands, timeout, prerequisite, and
success-only aggregate contract unchanged. Keep the manual compatibility
workflow's Windows Python 3.10 and 3.14 sessions unchanged and require that
manual gate before a release decision.

Pin the automatic matrix to exactly one Python 3.13 cell in workflow contract
tests. Expanding routine paid fan-out requires a future explicit decision and
measured justification.

## Consequences

- Automatic code events allocate two fewer Windows runners.
- Python 3.11 and 3.12 no longer run the focused portability subset on every
  change; automatic Python 3.13 and manual Windows boundary sessions carry the
  retained evidence.
- The stable aggregate continues to fail on missing, skipped, cancelled, or
  failed automatic portability evidence.
- The structural runner reduction is not a savings claim until a matched
  hosted run records durations and billed minutes after billing is restored.

## Alternatives

- **Keep all three automatic cells.** Rejected because it repeats a focused
  contract on the highest-cost runner class for every code change.
- **Make Windows portability entirely manual.** Rejected because routine code
  changes should retain one real Windows process-boundary signal.
- **Remove the manual Windows compatibility endpoints.** Rejected because
  release evidence must retain the supported Python version boundaries.
