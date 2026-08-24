---
title: "Worklog detail: close contextual advisory grammar"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [routing, classification, safety, validation]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
supersedes: []
superseded_by: null
type: worklog
commit: ca517872a3b55fa21a4350c841f35c6cba44ac9d
short: ca517872
date: 2026-08-24
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/318
related_issues:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
---

# Worklog detail: close contextual advisory grammar

## Purpose

Close independent-review gaps in AR-265 without returning to a brittle exact
phrase list or allowing malformed historical context to become routing
authority.

## Approach

The classifier now uses a bounded structural advisory grammar: discourse
lead-ins are removed, all accepted tokens must belong to a closed vocabulary,
and higher-precedence guards reject explicit actions and mutation obligations.
This covers common subjectless plan, options, priority, recommendation, and
suggestion forms while preserving execution authority for direct requests.

The transcript-free context and its source guard now require exact top-level
keys and exact non-boolean integer schema versions. Turn kinds remain
allowlisted. Source statuses accept only bounded identifier-shaped values so
legacy terminal rows such as `stopped` remain usable without accepting prose.

## Challenges encountered

The first post-repair decision-conformance invocation used the shared virtual
environment's installed console executable, which resolved the concurrently
changing shared checkout and supplied a stale test-node name. It stopped at
baseline with zero mutations executed and source unchanged. Invoking the CLI
module explicitly from the isolated worktree passed the baseline and complete
mutation gate.

## Decisions and alternatives

A narrow lifecycle enum was rejected because the Store deliberately preserves
legacy terminal identifiers. An unrestricted string was also rejected. The
bounded identifier grammar preserves compatibility while excluding prose and
control content. Advisory action verbs receive a targeted direct-request guard
rather than being globally executable, so `how should we proceed?` remains an
assessment while `can you proceed?` does not suppress execution authority.

## Verification

- Focused classifier, selector, Store, and inference slice: 268 passed.
- Named fast production spine: 806 passed, 20 skipped in 145.76 seconds.
- Worktree-local routing evaluation: every accuracy, latency, scale, and
  startup gate passed.
- Worktree-local decision conformance: baseline passed in 227.796 seconds; 151
  mutations killed, 0 survived, 0 invalid; source unchanged.
- Whole-tree Ruff check and format check passed; Git diff hygiene passed.
- Two bounded independent review passes completed; every actionable finding
  was repaired and covered by regression tests.

## Follow-ups

Tracker #317 and pull request #318 are published under the owner's explicit
authorization. Hosted checks, merge, exact-main installation, and the bounded
installed-host canary remain the next evidence gates. No live installed-host
header canary was run or claimed.
