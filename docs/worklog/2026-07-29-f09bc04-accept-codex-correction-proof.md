---
title: "Worklog detail: Accept one Codex correction in canary proof"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, canary, proof, finalization, continuation]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: f09bc04
short: f09bc04
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Accept one Codex correction in canary proof

## Purpose

Recognize the documented one-pass Codex header correction as a complete
activation chain once its authoritative accepted response closes the turn.

## Approach

The canary proof accepts either one direct terminal accept or exactly one
nonterminal correction followed by the sole terminal accept. It validates that
the correction has bounded missing-field evidence and a different response
hash. Every non-finalization cardinality remains exactly one, and the accepted
row must still own the run's terminal finalization identity and returned
response hash.

## Challenges encountered

Trace `019faf49-67bc-7953-8ff2-64f33173ae79` was a successful runtime chain:
one correction, one accepted rewrite, a completed run, and exact child evidence.
The legacy proof checker rejected it solely because it required one
finalization row rather than one authoritative terminal finalization.

## Decisions and alternatives

Permit one correction, not an arbitrary list of observations. This preserves
the hard one-pass retry bound while accurately representing Codex's current
Stop protocol.

## Verification

- All 22 Codex activation-canary tests passed.
- The new two-finalization proof regression validates exact terminal linkage
  and response hashing.
- Changed-file Ruff check and format, documentation validation, and diff checks
  passed.

## Follow-ups

Rerun the accepted source-live canary, persist its attestation, then execute the
named fast spine and PR flow.
