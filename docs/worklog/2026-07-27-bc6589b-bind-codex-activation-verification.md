---
title: "Worklog: Bind Codex activation verification to fresh proof"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, activation, canary, security]
related:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/worklog/README.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
supersedes: []
superseded_by: null
type: worklog
commit: bc6589b
short: bc6589b
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
---

# Worklog detail: Bind Codex activation verification to fresh proof

## Purpose

Make the documented verification command reachable without admitting generic
installation authority, and prevent old or malformed canary evidence from
being promoted as a fresh normal-profile activation proof.

## Approach

The parser marks one closed-world verification shape. The CLI branches before
configuration, installation, roster initialization, and dashboard work; binds
success to initial identity, a temporally fresh exact attestation, and matching
final inventory; and returns bounded resumable output. Existing-current Store
mode now crosses into spawned Codex hooks, uses SQLite read-write/no-create
mode, suppresses catalog reconciliation and gap hiring, and permits only normal
trace evidence plus attestation replacement.

## Challenges encountered

Independent reviews found that the first draft could accept a valid cached
proof, allowed the spawned hook to reopen an ordinary mutating Store, projected
malformed values unsafely, omitted the attended recovery action, and allowed
normal roster maintenance during the verification-only exemption. Each issue
was reproduced and closed before checkpointing.

## Decisions and alternatives

A generic operator-presence exemption and a full installer call were rejected
because both grant unrelated persistent mutation authority. A disclosure-only
allowance for roster changes was also rejected; the exact canary instead fails
closed when the existing catalog cannot satisfy its proof.

## Verification

- Dedicated AR-185 warning-strict regressions: 35 passed in 1.38 seconds.
- Focused authority, Store, parser, installer, and configuration package: 324
  passed with 6 platform skips in 30.23 seconds.
- Independent post-fix review packages: 136 passed; Store hardening 143 passed
  with 3 platform skips; proof-contract package 11 passed.
- Ruff and formatting passed; documentation validation passed for 469 files;
  `git diff --check` passed.

## Follow-ups

The exact installed artifact still needs one fresh current-profile canary and
correlated UI evidence under AR-180. Tracker creation remains pending outward-
write authorization.
