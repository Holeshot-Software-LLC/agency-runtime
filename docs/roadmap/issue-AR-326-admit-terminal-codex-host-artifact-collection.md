---
title: "AR-326: Admit terminal Codex host-artifact collection"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, host-artifact, finalization, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/core/evals/decision_conformance.py
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
blocks: [AR-297, AR-327]
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
- The regression-first repair keeps the default resolver and every hook caller
  live-only. Only the post-return backend collector requests an exclusive
  accepted-terminal mode. That mode requires one exact completed run, one bound
  `accept/completed` finalization with `missing=[]`, canonical non-pending
  metadata, and the existing session/trace, route, delivery, artifact, and
  invocation-window agreement.
- Three lifecycle regressions and two curated conformance mutations pass. The
  broader warning-strict Codex/artifact/host-canary review passes 203 tests.
  ADR-0189 records the durable lifecycle boundary.
- The named fast Python spine passes 860 tests with 3 skips under the protected
  Linux-capable Python 3.12 interpreter. The complete decision-conformance
  evaluator passes its baseline and kills all 165 mutations with no invalid or
  surviving result and source unchanged.
- Clean ledger `4b443be2` produces independently verified exact artifacts and
  five harness/dashboard images. A new clean Codex container passes its private
  input and preinstall-absence checks; its sole install remains the live gate.
- Clean Qwen2 ran that sole install with the explicit 300-second window. Codex
  exits 0 and the accepted terminal resolver now finds the exact parent, route,
  child artifact, Store decision, and receipt. Installation still exits 1 only
  because the receipt hashes the trusted rollout before Codex appends its final
  `task_complete` record; AR-327 owns that narrower replay mismatch.

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
- AR-327 preserves the terminal lookup and binds immutable receipt replay to
  the exact prior append-only Codex artifact prefix.

## Verification

Owner-private evidence is retained under
`~/.agency-runtime/evidence/ar326-terminal-collector-precheckpoint`. The
203-test affected suite, 17 decision tests, and two focused killed mutations
all exit 0 with empty stderr; their stdout SHA-256 values are
`4e76af29...a318`, `9cd8ed59...a033`, and `34858754...5cc7`.

The initially selected protected UV Python 3.13.13 binary hashes to
`1b6373b5...803d` and lacks `os.pidfd_open`. It therefore produced the retained
exit-1 858-pass/2-failure fast-spine receipt `27fd9352...e38a`, with the same two
native process-supervision tests failing again at `bd6cd01f...1f5b`. The exact
same named spine under Linux-capable Python 3.12.3 passes 860 tests with 3 skips
and exit 0 at `8cda02e1...4312`; stderr is empty.

The full evaluator cannot use the canonical `/usr/bin/python3.12` binary
directly because that canonical path has no pytest installation; the retained
baseline refusal exits 1 at `353d7910...8333` without changing source. Its
owner-private mode-0700 copy hashes to `1643dacd...1118`, exposes
`os.pidfd_open`, and carries pytest. Through that interpreter the complete
evaluator exits 0, passes its baseline, kills 165/165 mutations, reports zero
survived or invalid, and leaves source unchanged. JSON stdout hashes to
`891defed...ab8`; stderr is empty.

Exact `4b443be2` build, strict Twine, verifier, six image builds, and corrected
image verification exit 0. Wheel `aaf9b461...1f7d` is 9,341,603 bytes; sdist
`869b2842...545f` is 25,888,743 bytes. Manifest and image receipts hash to
`c8fdc3f6...9c9e` and `f91c05d1...adde`. The first OpenClaw image verifier
correctly refused Node 22.22.0 at stderr `e404ddeb...c427`; preserved failed
tags precede the passing Node 24.15.0 rebuild. Fresh Codex container
`cf983a11...79b1` passes absence receipt `0a7d2818...50cb` with no Agency target
installed and exact mode-0600 config `a4e213d6...7348`.

That container's sole install used the CLI default 180-second activation window
and timed out at Codex exit 124 immediately after a pending spawn dispatch,
before any native child route, delivery, finalization, or terminal parent
existed. Install JSON `40c1c188...7f5a` and content-free Store correlation
`5f76b443...6eaa` retain the failure; Store quick-check passes. This run neither
proves nor disproves terminal collection. A second exact clean container passes
fresh absence at `1849d13e...a74c` and will use the previously proven explicit
300-second activation window for its sole install.

## Acceptance

- [x] Regression proves the current live-only resolver disappears after an
      accepted terminal commit while the bounded backend resolver remains exact.
- [x] Hook-side callers remain live-only and terminal, ambiguous, rejected, or
      stale runs cannot create host-delivery authority.
- [ ] A rebuilt fresh one-install Codex container collects the canonical child
      artifact, persists current-profile attestation, and exits 0.
- [x] Focused warning-strict and named repository checks pass.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
