---
title: "Worklog detail: Accept documented Codex spawn nickname"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, hooks, delegation, receipts]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 01150cd
short: 01150cd
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Accept documented Codex spawn nickname

## Purpose

Complete Codex v0.146 activation-receipt binding when the successful native
spawn result includes its documented optional `nickname` field.

## Approach

The PostToolUse boundary accepts only `task_name` or `task_name` plus
`nickname`. It projects either representation into the same three exact
lifecycle identity fields and discards the display-only nickname before the
existing rooted-label, task-name, persisted-child, and one-use grant checks.

## Challenges encountered

The preceding source canary and exact-installed rerun both spawned, waited for,
and completed the specialist, yet left the activation grant unconsumed. The
mapping-only hypothesis did not survive the exact-install test. Authoritative
Codex v0.146 source showed that the JSON-string result may include `nickname`,
which Agency's strict raw-field equality check rejected.

## Decisions and alternatives

The repair does not accept arbitrary future response fields. A regression test
proves an extra field still fails closed, while another proves the nickname is
not retained in lifecycle evidence.

## Verification

- Four exact spawn-receipt regression tests passed.
- The full receipt test file passed 35 tests with 2 platform skips.
- The named fast Python production spine passed 651 tests with 6 skips.
- Ruff check and format passed all 601 Python files.
- Dashboard UI verification passed all 109 tests.
- Metadata, policy, worklog, documentation, and diff checks passed.

## Follow-ups

Merge and exact-install this commit, then rerun the isolated Codex activation
canary. Only live activation consumption, specialist load, delegation, header,
and attestation evidence can prove the boundary repaired.
