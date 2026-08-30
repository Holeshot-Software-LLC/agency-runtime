---
title: "Reconcile Codex canary callback order"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, native-child, transactions, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/store/native_child.py
  - tests/test_canary_activation_snapshot.py
supersedes: []
superseded_by: null
type: worklog
commit: ced8363177d6da1863969badc74e84c87e37dd34
short: ced83631
date: 2026-08-27
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
---

# Worklog detail: Reconcile Codex canary callback order

## Purpose

Repair the exact Qwen-backed no-bypass Codex production-container transaction
after it proved full v6 child delivery and exit-0 execution but left the real
child unbound to the parent spawn dispatch. Preserve ordinary encrypted-spawn
diagnostics and every existing route, artifact, header, finalization, and
attestation gate.

## Approach

The exact managed canary exception now recognizes the existing bounded Codex
ciphertext plus the fixed task and response shapes. It avoids appending the
ordinary opaque-channel failure only for that already-proven parent. When
`PostToolUse` arrives first, the hook records one fixed-unit synthetic pending
dispatch. A later validated `SubagentStart` atomically rekeys that row and its
delegation to the host-authored UUID, or merges the dispatch into a concurrently
observed unbound real worker. The opposite order keeps the direct real-child
path and may claim the exact dispatch after an already-observed terminal child.

Conflicting identities, work units, dispatches, ambiguous pending rows, terminal
parents, wrong canary shapes, and ordinary processes remain rejected. Replays
are idempotent. Snapshot-only verified-delivery projection then supplies the
specialist identity to both the Store-backed header and ready-routing receipt.

## Challenges encountered

The live transaction contained two independent defects. The encrypted
`PreToolUse` path truthfully appended an ordinary inference-failure route before
the later restricted child succeeded, invalidating the ready receipt. Separately,
Codex delivered `PostToolUse` before `SubagentStart`, so the synthetic delegation
used the opaque-message hash as its unit while the successful real child used
the fixed canary unit and had no delegation or execution tool-use ID.

Both host callback orders can overlap across hook processes. The repair therefore
cannot assume a sequence or use a read-then-write join. One immediate SQLite
transaction owns the identity promotion, preserves the original dispatch
timestamp, detects a pre-existing real row, and rolls back both projections on
conflict.

## Decisions and alternatives

[ADR-0144](../decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md)
already requires first-complete-callback reconciliation; no new architectural
decision was needed. Deterministically rewriting the encrypted parent message,
trusting the synthetic task identity as the real worker, deleting the ordinary
diagnostic globally, or weakening ready-routing/header validation were rejected.
ADR-0179 and ADR-0188 continue to bound the exception to the exact managed
canary and host-authored parent/child lineage.

## Verification

- Five targeted warning-strict cases cover exact suppression, ordinary opaque
  diagnostics, pending rekey, overlapping merge, conflicting-real rejection,
  the opposite callback order, replay, header projection, and ready receipt.
- The affected hook/Store/header/parity set passes 149/149; stdout SHA-256 is
  `394d9276...1c4d`, exit 0, and stderr is empty.
- A separate security/atomicity set passes 145/145 at `ae7689e3...7a84`, exit 0,
  and empty stderr. Decision-conformance tests pass 17/17 at
  `74a9f4f9...4141`; both new mutations are killed at `ea4477e5...3695` with
  source unchanged.
- Documentation validation passes for 893 files at `c5d005ae...18ac`;
  repository-wide Ruff/format passes at `94423e2d...0564`; diff-check output and
  every retained stderr are empty.

## Follow-ups

- Build and independently verify new exact artifacts/images from this clean
  checkpoint, then run one fresh no-bypass Codex production install. Never
  relabel the prior failed container as repaired evidence.
- Continue the remaining Claude, Hermes, OpenClaw, ordinary-process,
  host/dashboard, repository-gate, and final teardown packages under AR-297.
- Tracker creation remains prohibited until the owner explicitly authorizes it.
