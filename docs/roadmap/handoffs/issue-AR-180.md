---
title: "AR-180 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-09-07
tags: [handoff, codex, native-child, hooks, compatibility]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-180
branch: codex/ar180-live-proof-reconciliation
evidence_commit: fdb010ffb0a5eab4b545781b047a2743e6372418
minimum_ledger_commit: 6220ca6134a1aa5ddd5fc34b9d6e703d9ac32631
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-180 active recovery capsule

## checkpoint

The September 7 reconciliation replaces the stale August 25 capsule.
AR-180 stays open; original acceptance states remain unchanged.
Main source checkpoint fdb010ff includes accepted AR-407; its merge ledger is
6220ca61. The current bounded package records existing live evidence and
changes no runtime behavior or owner configuration.

## completed-evidence

- Codex CLI 0.153.4 Linux exec depth one current-profile activation completed
  at 22:04:41Z, runtime4329d760, install c482c4e2, bundle0734429d.
- Trace01a07de5-15c3-7350-86c4-b38e886caa61 binds exact parent, one child,
  inference decision, one code-reviewer card and immutable delivery receipt.
- Child record8 contains complete v6 additional context at22:04:05.696Z,
  preceding first non-input response at22:04:05.698Z and final at22:04:21.161Z.
- Card bytes, envelope, nonce, lineage and sealed artifact prefix agree.
  Read-only immutable-receipt verification returns verified/pre-speech/v6.
- Actual five-field parent header and final body hash match the sole accepted
  finalization; the installation-bound v4 attestation persists.
- No new provider request was needed for this correlation. SQLite was opened
  mode=ro/query_only; no Store construction or new evidence row.

## exact-blocker

This is restricted one-card exec proof under ADR-0179/0193, not ordinary
encrypted-spawn, TUI, Desktop or multi-card proof. The same card occurs in
the parent's developer context, so criterion8's "only in child context" is
not literally met. The restricted canary forbids companions and cannot
satisfy criterion9 by repetition. No original criterion is silently waived.

## same-task-continuity

Continue in the same task after a clean checkpoint. Owner authorized fanout
and normal PR/merge publication, oldest-first, until September8 01:00UTC.
No threshold-driven task transfer, empty commit or waiting requirement.

## next-bounded-work-package

1. Publish this exact proof/retained disposition by normal PR/merge.
2. Continue AR-181 smoke reconciliation, then183/184/185.
3. When addressing AR-180 itself, reconcile child-only wording explicitly and
   use appropriate separate TUI/Desktop/multi-card live surfaces.
4. Do not repeat an unchanged one-card canary for impossible shape coverage.

## verification

The read-only card/artifact/receipt/finalization correlation passed.
This records package runs metadata, policy, worklog, docs, tracker, Ruff and
diff checks. Latest reused AR-407 production checks:1085/three skips, UI224,
fresh-wheel MCP/dashboard and generated all-host smoke8/0/0.
These are not newly run AR-180 tests or new host canaries.

## constraints

No new credentials, trust bypass, provider-profile changes or native Windows.
No raw private card/rollout body in the repository; portable hashes and exact
identities are retained in the evidence receipt. Do not restore removed grant
organs, weaken current host-artifact validation or copy the canary's header
into the still-unverified ongoing parent session.
