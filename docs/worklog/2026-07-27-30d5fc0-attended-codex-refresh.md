---
title: "Worklog detail: attended Codex refresh transaction"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, installation, security, operator-presence]
related:
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
supersedes: []
superseded_by: null
type: worklog
commit: 30d5fc0b1fb9cdef54a607681bde1f1a55af8994
short: 30d5fc0
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: attended Codex refresh transaction

## Purpose

Add one production-shaped positive installation slice without granting the
generic multi-host installer broad persistent-mutation authority. The slice
repairs an existing managed, registered, and enabled Codex integration and
keeps installation completion distinct from runtime activation.

## Approach

The coordinator prepares an immutable binding over configuration, Store and
control generations, the existing managed tree, the candidate and launcher
plan, the exact Codex executable/environment/version, and strict native
inventory. A pinned Windows helper displays that transaction and obtains a
non-exporting Windows Hello result. The coordinator then locks, prepares again,
atomically publishes the target with an exact backup, refreshes only the Agency
plugin registration, and proves filesystem, launcher, inventory, source,
version, enablement, and policy postconditions. Bounded identity-checked
compensation restores the prior tree and registration or reports manual
recovery with retained evidence.

## Challenges encountered

Independent reviews found and repaired a base-version/cachebuster comparison,
unstructured compensation exceptions, incorrect partial-state reporting,
pre-commit JSON/text recovery claims, and a native parser that ignored
malformed non-object inventory rows. The final contract deliberately remains a
refresh rather than a missing-host bootstrap, and it cannot infer that a newly
registered plugin has loaded in the current Codex process.

## Decisions and alternatives

ADR-0104 records why the exact existing-install transaction is admitted while
fresh bootstrap, generic installation, transferable verification receipts, and
registration-as-activation are rejected.

## Verification

- 341 focused prepared-install, parser, registration, native-helper, launcher,
  and filesystem tests passed warning-strict.
- 105 dashboard UI tests passed.
- Repository-wide Ruff check and format check passed.
- High-severity Bandit scan of the touched Python transaction boundary passed.
- Documentation metadata, policy availability, worklog, documentation, and Git
  diff checks passed.
- The native helper was deterministically rebuilt in two roots with pinned
  source and executable identities.

## Follow-ups

- AR-143 still requires an attended refresh plus restart/new-task current-
  profile canary and broader positive-operation coverage.
- AR-160 still owns hosted cross-platform artifact evidence.
- AR-161 remains blocked on owner publisher identity, signing-key custody,
  authorized legal disposition, and signed-delivery verification.
