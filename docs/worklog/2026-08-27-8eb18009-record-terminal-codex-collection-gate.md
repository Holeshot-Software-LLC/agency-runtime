---
title: "Record terminal Codex collection gate"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, codex, canary, host-artifact, finalization, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
supersedes: []
superseded_by: null
type: worklog
commit: 8eb180094ddbfee0c9e79381ca602e5e31f907d6
short: 8eb18009
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
---

# Worklog detail: Record terminal Codex collection gate

## Purpose

Preserve the exact rebuilt AR-297 Codex evidence at a clean recovery boundary.
The fresh run proves AR-325's callback reconciliation and accepted
finalization, while isolating a later post-return host-artifact collection bug
as AR-326 instead of relabelling the failed install as successful.

## Approach

The roadmap and active capsule now bind clean ledger `19e0210b`, its verified
artifacts and images, the fresh absence receipt, the one no-bypass install, and
the correlated parent, child, dispatch, native delivery, finalization, and Store
identities. A content-free diagnostic established that the exact child route
remains present after completion but the backend collector's live-only parent
resolver no longer admits the accepted terminal run.

AR-326 freezes the repair around one explicit terminal-parent mode for the
bounded post-return backend collector. Hook-side lookups stay live-only, and a
terminal candidate must retain the exact accepted finalization and native
host-delivery graph. Existing evidence remains a failed attestation and must be
replaced by a newly built, newly installed proof after the source repair.

## Challenges encountered

The visible install failure occurred after all native child execution and
finalization checks had succeeded. The independent collector runs only after
Codex exits, at which point its shared resolver deliberately excludes completed
parents. That lifecycle ordering made a valid accepted graph undiscoverable
without weakening any of the evidence itself.

## Decisions and alternatives

No activation bypass, live-hook widening, artifact relabelling, or ordinary-run
fallback is accepted. The implementation-level durable security boundary will
be recorded with the AR-326 repair after regression evidence fixes its exact
shape. Tracker creation remains prohibited by the active task.

## Verification

- Metadata validation passes for 895 Markdown files.
- Policy-availability and generated-worklog checks exit 0.
- Documentation validation passes for all 895 maintained Markdown files.
- `git diff --check` exits 0 with empty output.

## Follow-ups

- Implement AR-326 regression-first, retain hook-side live-only authority, and
  record the terminal collector boundary in a durable decision.
- Rebuild exact artifacts and images from the resulting clean ledger, then run
  one new clean Codex production-container install.
- Continue the remaining AR-297 harness, ordinary-process, host/dashboard,
  named-gate, and final teardown packages.
