---
title: "Bind AR-180 to current live child evidence"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, codex, live-evidence]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: bb83cd6034a20201943f501950fba0a991997d3a
short: bb83cd60
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/730
related_issues:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Bind AR-180 to current live child evidence

## Purpose

Replace a stale blanket activation blocker with exact current native evidence
without closing the broader unfinished record.

## Approach

Correlate the existing current-profile CLI0.153.4 exec depth-one host artifacts,
immutable v6 delivery, exact card bytes, lifecycle, final body and v4
attestation. Preserve original acceptance states and historical evidence.

## Challenges encountered

The later child artifact is append-only: its sealed99,897-byte prefix matches
the receipt even though its final whole-file hash differs. The same card
occurs in the parent, so the child-only requirement is not satisfied.
The fixed one-card restricted canary cannot prove multi-card support.

## Decisions and alternatives

Apply accepted ADR0179/0193 to the restricted canary, not ordinary encrypted
calls. Do not restore removed grants, rerun an incapable shape, waive Desktop
or fabricate acceptance verdicts. No new product policy is established.

## Verification

Read-only mode=ro/query_only correlation succeeds. Precise identities, hashes,
ordering, output and limitations are in the receipt. Publication checks cover
metadata, policy, worklog, docs, tracker, Ruff and whitespace. Existing AR407
fast-spine/UI/artifact checks are reused, not represented as new native tests.

## Follow-ups

AR180 remains open. Publish normal PR/merge, then AR181. Separate shape and
child-only policy reconciliation remain necessary for umbrella completion.

Substantive `bb83cd60` records exact existing native proof and replaces the active recovery projection, while retaining all original acceptance states.

Publication `24eede12` merged PR #730 at2026-09-07T23:07:23Z. AR180 remains open with exact restricted proof and explicit broader holds.
