---
title: "AR-326: Admit terminal Codex host-artifact collection"
status: open
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, host-artifact, finalization, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/evidence.py
  - tests/test_canary_activation_snapshot.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-326
priority: p0
tracker_url: null
depends_on: [AR-325]
blocks: [AR-297]
---

# AR-326: Admit terminal Codex host-artifact collection

## Problem

The fresh exact `19e0210b` Codex run accepts its first finalization and persists
the real child's native delivery receipt, but the backend's independent
host-artifact collector runs only after Codex returns. Its route resolver admits
only a still-open parent, so the now-completed accepted run becomes invisible
and current-profile attestation fails with `verification_refused`.

## Current state

- Exact build, strict Twine, distribution verification, six image builds, and
  image verification exit 0. Wheel `81d0bba7...43c1` and Codex image
  `30ffdb63...9819` bind clean ledger `19e0210b`.
- Fresh absence `dd5b6e71...c301` exits 0. The sole no-bypass install JSON
  `4c3e1e1b...c97e` exits 1 after accepted finalization
  `d5b3d58f-c94d-418f-b857-9a4c07de928c` with `missing=[]`.
- Parent `01a0435e...ac6f`, trace `01a0435e...aeb0`, child
  `01a0435f...02ac`, native decision `native-child-98105e66...a7a6`, complete
  v6 prompt hash `e409b2c8...20bd`, verified delivery, exit-0 child, valid
  header, and one completed wait all agree.
- Content-free diagnostic `89fafc05...5b02` proves the child route remains but
  `get_codex_activation_canary_parent_snapshot` returns no parent after the
  accepted terminal commit. Store `ceb65010...2fc8` passes SQLite quick-check.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Keep every hook-side route lookup live-only. Give only the backend's bounded
post-return collector an explicit terminal-parent mode that admits one exact
completed run with one authoritative accepted finalization, no missing fields,
the same session/trace, and the existing native route and delivery receipt.
Continue to require the independently parsed canonical child rollout inside the
measured invocation window; reject active/terminal ambiguity, continuation or
rejection finalizations, stale artifacts, and every ordinary process.

## Dependencies

- AR-325 supplies the accepted first-pass finalization and exact real-child
  reconciliation that exposes this later lifecycle mismatch.
- ADR-0156 and ADR-0179 continue to require host-authored delivery evidence;
  terminal lookup may locate that evidence but cannot replace or manufacture it.

## Acceptance

- [ ] Regression proves the current live-only resolver disappears after an
      accepted terminal commit while the bounded backend resolver remains exact.
- [ ] Hook-side callers remain live-only and terminal, ambiguous, rejected, or
      stale runs cannot create host-delivery authority.
- [ ] A rebuilt fresh one-install Codex container collects the canonical child
      artifact, persists current-profile attestation, and exits 0.
- [ ] Focused warning-strict and named repository checks pass.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
