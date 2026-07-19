---
title: "AR-59: Schedule delegation DAG nodes as dependencies complete"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-18
tags: [delegation, dag, concurrency, performance, correctness]
related:
  - docs/decisions/0054-unit-aware-assignment-and-event-driven-dag.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: performance
issue_id: AR-59
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/60"
depends_on: [AR-27, AR-58]
blocks: [AR-82]
---

# AR-59: Schedule delegation DAG nodes as dependencies complete

## Problem

Executing a dependency graph one topological level at a time creates an
unnecessary barrier: a fast branch waits for every unrelated node in the level
before its own successor can start. It also delays failure propagation and
wastes bounded worker capacity.

## Current state

The dispatcher now maintains dependency counts and a stable ready queue. It
submits ready units up to the worker bound, reacts to the first completed
future, releases successful successors immediately, and recursively marks a
failed unit's descendants skipped without blocking independent branches.

## Approach

Retain topological validation for cycle and dependency correctness, but execute
from events rather than level barriers. Use deterministic unit-ID ordering for
simultaneously ready or completed work, never exceed the configured worker
bound, and admit a child only after every predecessor has an authoritative
successful result.

## Dependencies

AR-27 defines the strict success and failure evidence needed to release a child.
AR-58 gives each scheduled unit an accurate recommended specialist.

## Acceptance

- [x] A successor starts as soon as all of its own dependencies succeed.
- [x] Unrelated slow work does not hold a ready branch behind a level barrier.
- [x] Failed or malformed prerequisite results skip every dependent descendant.
- [x] Independent branches continue after an unrelated failure.
- [x] Ready and completion handling remain deterministic under concurrency.
- [x] The configured worker bound is validated before delegation side effects.
