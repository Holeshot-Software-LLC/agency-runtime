---
title: "Bind AR-185 to exact installed activation proof"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, codex, activation, evidence]
related:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 500de0850deb7c18286caba64de3f45d276c54ce
short: 500de085
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
---

# Worklog detail: Bind AR-185 to exact installed activation proof

## Purpose

Complete the stale verification-only record using exact current installed
evidence, without conflating owner refresh, native trust or broader delivery.

## Approach

Trace exact parser/branch, existing-only Store, temporal attestation binding and
bounded failure output. Add fresh274 focused results and installed328module/
14helper identity checks; correlate the existing current-profile v4/v6 proof.

## Challenges encountered

Criterion2 was broader than the intended no-bypass slice; explicitly scope it
while retaining separately supported autonomous/managed modes. Criterion3's
attended-only wording predates ADR0117; correct only owner authority while
retaining exact preparation. Preserve both originals and do not invent new
TUI approval or whole-main installation.

## Decisions and alternatives

Apply existing ADR0117/0173/0179/0193, no new policy. Reuse the actual bounded
live proof rather than rerun it for paperwork. AR180 still owns TUI/Desktop/
multi-card and child-only requirements.

## Verification

Fresh175+71+28=274passes;40Windows exclusions. Current installed verification
path is source-equivalent despite unrelated AR131/407 deltas. Candidate500de085
freezes all9 builder groups; only isolated verdicts can authorize completion.

## Follow-ups

Freeze, inspect excerpt budgets, run nine isolated acceptance checks, then
normal PR/merge. No runtime change or provider-profile mutation in this package.

Substantive `500de085` freezes exact source/live evidence and explicit existing-policy reconciliation; the builder does not assign acceptance verdicts.
