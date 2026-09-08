---
title: "AR-404 final exact-main installation and evaluation"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [delivery, installation, verification]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues: [docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md]
---

# AR-404 final exact-main installation and evaluation

## Purpose

Honor the owner's stopping-point request after the code-first fanout: finish
existing slices, publish them normally, install exact main and inspect native
behavior without relying on unit or installer success claims.

## Approach

Five serial source PRs preserve independent ownership, review and exact ledgers.
Freeze4cbebf73, build/verify artifacts, compare all614 installed payload files,
run five normal host installers, then separate actual native checks from smoke.

## Challenges encountered

One card assertion confused content and decorated-card byte limits; corrected
test-only. Decision conformance baseline hit ambient private-path permissions;
private-umask rerun exceeded180s with no verdict. Main's ignored Claude settings
made strict build refuse; an exact clean detached tree passed without deleting
the user's file. OpenClaw refuses native replacement while its gateway is live.

## Decisions and alternatives

No extra backlog scope, direct-main commit, trust bypass, credential creation,
shared service restart without approval or fabricated loaded/header evidence.
Advisory staged pointers do not establish native installation or activation.

## Verification

Exact source/installed counts, hashes, timestamps, test failures and scoped
successes are in the linked final delivery receipt. Native evidence is pending
at this pre-evaluation clean checkpoint; no all-host pass or release claim.

## Follow-ups

Complete bounded native evaluation, record exact remaining blockers, merge this
evidence and final ledger normally, and stop until the owner asks to continue.
