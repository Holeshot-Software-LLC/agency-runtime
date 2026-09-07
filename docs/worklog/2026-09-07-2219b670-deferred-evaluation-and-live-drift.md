---
title: "Retain AR-178 and record the live scoped-install defect"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, evaluation, live-evidence]
related:
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 2219b67054f23ab551971f3fd2a11b903a39e889
short: 2219b670
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
---

# Worklog detail: Retain AR-178 and record the live scoped-install defect

## Purpose

Reconcile the next oldest record honestly and retain the concrete live-hook
diagnosis produced by owner-requested parallel investigation.

## Approach

AR-178 remains open/deferred under existing ADR-0102. Its six scenario
definitions and live validator are implementation, not a completed matched
blind-graded study. Original criteria and tracker #153 OPEN state are preserved.

AR-407/#727 records an independently reproduced output bug: scoped Codex
install takes the first all-host drift and misattributes OpenClaw's older
package. Codex disk/cache are current; this running process separately
retains old hooks and lacks the configured launch credential.

## Challenges encountered

Earlier residual-warning interpretation conflated per-host pointers. The
live audit corrects it without rewriting dated failures or claiming parent
recovery. Existing key-file presence does not establish process inheritance.
No secret values, raw private prompts or manual trust changes were used.

## Decisions and alternatives

Keep intentional research and preserved evaluators; do not retire by age.
The scoped warning fix uses existing per-host authority, not a new policy.
No runtime credential-file fallback, OpenClaw replacement or repeated canary.

## Verification

Read-only source/ADR/criteria review; tracker #153 read back OPEN. Strict
metadata, policy, worklog, docs, tracker, Ruff, formatting and diff checks pass.
No code changes or new native-turn claims in this reconciliation.

## Follow-ups

Publish AR-178, then AR-180. Separately review, live-check and publish AR-407's
bounded implementation. AR-176 inventory and AR-181 smoke investigations
do not silently change their acceptance verdicts.

Substantive `2219b670` preserves AR-178 and records the newly reproduced AR-407 bug; no completion verdict is fabricated.
