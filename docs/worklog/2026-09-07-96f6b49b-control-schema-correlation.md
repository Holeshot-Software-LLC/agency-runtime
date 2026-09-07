---
title: "Preserve correlation when the current control contract is invalid"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, correlation, regression, backlog]
related:
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/roadmap/acceptance/evidence/AR-175-control-boundary-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 96f6b49b2a8e92f7b63704853eedcd06b5ebd0c1
short: 96f6b49b
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
---

# Worklog detail: Control-schema error correlation

## Approach and challenges

The unsupported legacy fallback is already absent. Twenty direct cases exposed
eight actual empty request IDs on missing/wrong schema, null and malformed JSON
in both refresh paths. Move only schema validation into the existing API
callback so its safe request ID survives. Keep refresh owners responsible for
ignoring abort, lifecycle and obsolete-generation work; all eight cancellation
cases already passed and still pass. No fallback or authority expansion.

Add 24 corresponding schema/JSON fault-and-recovery cases to the reusable
optional browser checker, across both refresh methods and all three existing
viewport widths. Count zero POSTs and no legacy request fanout explicitly.
The real browser is pending until the exact clean wheel is built.

## Verification

Red: 12 pass/eight fail (90.349807ms). Green: all 20 pass (88.819304ms).
Full UI: 224 pass, 250.156288ms, 96.93/86.78/95.74 against unchanged floors.
Four resource/floor gates pass; current assets 386965 bytes, 107 below strict
378 KiB. The source change removes 74 bytes; no budget increase or minification.
Fresh named spine: 1085 pass/three existing skips, 69.72s.
Ruff and strict docs/diff pass after the raw failure transcript's file-URI
scheme was stripped for the repository documentation rule; all assertions,
paths, failure counts and line numbers remain. The rejection is recorded.

## Decisions and follow-ups

Only stale criterion 6 follows existing ADR-0105; preserve original wording
and criteria 1–5. The old 257620-byte asset total is historical, not current.
Checkpoint source/ledger before private wheel-backed browser execution, then
complete six isolated criteria and one normal PR/merge before AR-176.
No native Windows, owner profile, credential or normal-host activation claim.
Stop cleanly at 9 p.m. Eastern September 7.

## Initial clean source checkpoint

96f6b49b (96f6b49b2a8e92f7b63704853eedcd06b5ebd0c1) records the reproduced control-boundary repair, direct tests,
current gate receipts and optional browser-checker extension. This immediate
ledger preserves the smallest tested source slice before exact-wheel QA.

## Pre-browser checkpoint

bab4b475 (bab4b475545ae5a044d198fd2b645f51313e2d25) pins the source repair and remaining installed-wheel browser evidence in the active capsule. The next bounded package builds that clean source and checks actual responses, correlation headers, retention, and recovery before any completion claim.
