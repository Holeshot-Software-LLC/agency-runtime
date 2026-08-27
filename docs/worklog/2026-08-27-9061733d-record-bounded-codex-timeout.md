---
title: "Record bounded Codex timeout"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-326, codex, timeout, container, recovery]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/handoffs/issue-AR-297.md
supersedes: []
superseded_by: null
type: worklog
commit: 9061733d2ccc2bd81ef472827bb62a61bfb3129c
short: 9061733d
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
---

# Worklog detail: Record bounded Codex timeout

## Purpose

Preserve the first rebuilt Codex container's sole timed-out install without
misclassifying it as an AR-326 terminal-collector result, and bind the next
fresh container to the previously proven 300-second activation window.

## Approach

The exact one-install JSON, parent and child rollouts, and SQLite Store trio were
copied into owner-private evidence after process exit. A content-free Store
projection proves the sole accepted staffing route, pending synthetic dispatch,
absence of native route/delivery/finalization/attestation rows, and final
`canary_failed` cleanup state. SQLite quick-check passes.

The CLI default is 180 seconds. This run reached Codex exit 124 immediately
after dispatch and never created a terminal parent, so it did not exercise the
accepted-terminal collector. A second container was created from the same exact
image ID, received the same private auth and mode-0600 config, and passed fresh
absence. Its sole install will use explicit `--activation-timeout 300`, the
window used by the prior transaction that completed a real child and accepted
finalization.

## Challenges encountered

The missing explicit timeout was operational, not a model or product-config
change. Reinstalling the first container would violate the one-install evidence
boundary, so it remains retained as failed evidence and a second clean
container owns the corrected live attempt.

## Decisions and alternatives

No retry occurs in place, no failed evidence is relabelled, and no activation
bypass or model-route change is introduced. Because no terminal graph existed,
this result cannot be used to assess AR-326 either positively or negatively.

## Verification

- Sole install JSON `40c1c188...7f5a` exits 1 with empty stderr and records
  Codex exit 124 under managed policy with no trust bypass.
- Store `e7bc0f97...9c55` passes quick-check; content-free correlation
  `5f76b443...6eaa` proves zero native assignments, delivery receipts,
  finalizations, and attestations.
- Parent and child rollout hashes are `586e8285...3de2` and
  `fba3e1f9...35e9`.
- Second container `9806a82a...2a2b` passes fresh absence at
  `1849d13e...a74c`; no install has run there.
- Metadata, policy availability, worklog, docs, and diff checks pass; the
  recovery capsule remains within 170 lines and 9,201 bytes.

## Follow-ups

- Run the second container's sole no-bypass install with the explicit
  300-second activation window and retain its full exact evidence graph.
- Continue AR-297 only from the resulting truthful live verdict.
