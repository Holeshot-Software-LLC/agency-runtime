---
title: "Scope trusted Windows bootstrap root ownership"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [windows, security, ci, portability]
related:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0056-capability-bound-restricted-windows-scratch.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 31516d1
short: 31516d1
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Scope trusted Windows bootstrap root ownership

## Purpose

Make the protected CI bootstrap root portable to elevated Windows hosts without
weakening the current-user and logon-private boundaries used by application
state, Codex scratch allocations, or their descendants.

## Approach

Represent the persistent bootstrap root with an explicit internal authority
kind. Its receipt may accept ownership by Builtin Administrators, LocalSystem,
or TrustedInstaller in either canonical alias or SID form, but only after a
single captured SDDL proves a protected private DACL, prospective-child safety,
current-token mutation access, and the existing pinned file identity. All other
guarded identities retain the stricter current-user-owner check.

Separate Windows principals that may appear in access entries from principals
that may own a durable filesystem object. This prevents Creator Owner and Owner
Rights placeholders from being promoted into trusted owners. Revalidate the
protected-DACL bit on every bootstrap authority use so a later inheritance
downgrade invalidates the process-local receipt.

## Challenges encountered

GitHub's elevated Windows token canonicalized an atomically created current-user
descriptor to a protected root owned by a system authority. Earlier validation
reported only a generic mismatch; bounded stage diagnostics isolated the exact
owner mismatch. An adversarial review then found that the first implementation
did not re-check DACL protection after creation, and a malformed test SDDL would
have exercised owner rejection instead of the intended protection gate. Both
were corrected before commit.

## Decisions and alternatives

- Do not relax the global current-owner predicate. The exception is typed and
  limited to the persistent bootstrap authority root.
- Do not accept arbitrary privileged-looking or pseudo-principal owners.
  Creator Owner, Owner Rights, creator SIDs, broad principals, and unrelated
  account SIDs fail closed.
- Do not repair an existing collision by path. Reuse still requires the pinned
  parent and root handles, a protected private ACL receipt, and current-token
  usability.

## Verification

- `370 passed, 4 skipped` across the combined Windows ACL, private-path,
  CI-runtime, subprocess-authority, and low-level security regression set.
- The corrected protected-DACL regression cases passed `6 passed` and exercise
  empty, auto-inherited, and protected controls explicitly.
- An unrestricted local Windows CI-runtime bootstrap completed successfully.
- Repository-wide Ruff check, Ruff format check, and `git diff --check` passed.
- Independent adversarial re-review reported no remaining actionable findings.

## Follow-ups

Run the full hosted Windows and Linux matrix for PR #104 and record its immutable
head/run evidence in AR-104 before completion.
