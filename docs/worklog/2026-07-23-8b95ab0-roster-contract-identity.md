---
title: "Reconcile governed contract identity with opaque roster hashes"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, roster, workforce, identity, AR-119, green-main]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
supersedes: []
superseded_by: null
type: worklog
commit: 8b95ab0
short: 8b95ab0
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
---

# Worklog detail: fix(roster): reconcile governed contract identity with opaque roster hashes

## Purpose

Two latent identity-boundary problems in `core/store/roster.py` became
visible once PR #129 wired `project_workforce_contract` into every
activation path: opaque upstream roster hashes hard-failed the workforce
contract's SHA-256 `version_hash` check (D1), and a tampered or
opaque-divergent row hash crashed snapshot decode with `RuntimeError`
instead of letting the continuation guard reroute (D2).

## Approach

The codebase has two distinct identity concepts that must not be
conflated:

- **Roster layer** (`store/version_identity.py`,
  `roster/revisions.py`): deliberately supports bounded opaque upstream
  version tokens (up to 256 bytes) because not every upstream source
  uses SHA-256. `content_identity_matches` returns True for opaque
  identities.
- **Workforce contract layer** (`workforce/contract._content_hash`):
  requires an exact SHA-256 digest for the governed contract
  `version_hash`.

- **D1** (`_prepared_roster_agent`): pass `content_digest(content)` as
  the contract `version_hash` instead of the roster row's opaque
  `content_hash`. The roster row keeps its opaque `content_hash`
  separately for replay identity.
- **D2** (`_decoded_roster_rows`): keep the hard `RuntimeError` guard
  for genuine corruption (`agent_id` or `version` mismatch) but stop
  treating a stale or tampered row hash as corruption. Content-hash
  consistency is still enforced on the content-reading paths via
  `content_identity_matches` (lines ~1480, ~1547), and the continuation
  guard detects staleness and reroutes.

## Challenges encountered

- An intermediate D2 attempt used `content_identity_matches` with two
  hash strings as both args; that has wrong semantics (it hashes the
  first arg). The D2 test tampers to a valid-shape digest (`"a"*64`) and
  expects graceful reroute, so the snapshot reader must not raise on ANY
  hash mismatch — hash staleness is the continuation guard's job. The
  final fix drops the hash clause from the raise entirely.
- Verified net effect: `test_durable_continuation.py` went from 6
  failures (base `effa10b`) to 5 with this change — the D2 test now
  passes and no new failure was introduced. The remaining 5 are a
  separate pre-existing durable-continuation cluster (unit-agent-plan),
  not caused by D1/D2.

## Decisions and alternatives

- Reconcile the two identity layers rather than weaken either: the
  roster layer keeps opaque tolerance; the contract layer keeps its
  SHA-256 invariant.
- Rejected: raising on hash mismatch in the snapshot reader. That
  pre-empts the continuation guard and crashes decode on stale state.
- Rejected: adding defaults to make `version_hash` optional. That would
  weaken the governed-contract invariant.

## Verification

- `test_final_activation_boundaries_allow_legitimate_accents_and_opaque_identity`
  and `test_active_revision_mismatch_is_detected_even_with_tampered_snapshot_ids`
  both pass.
- `test_direct_store_rejects_mismatched_digest_identity_without_writes`
  still passes — genuine digest tampering is still rejected on the
  content-reading paths.
- Full `tests/test_roster_remediation.py` -> 132 passed.
- `test_durable_continuation.py`: 5 failures remain, all pre-existing on
  `effa10b` (verified by stash); this commit fixed the 6th (D2) and
  added none.
- `ruff check` + `ruff format --check` clean.

## Follow-ups

- The 5 remaining `test_durable_continuation.py` failures are a separate
  PR-#129 cluster (unit-agent-plan / continuation), to be triaged in the
  P0d test-align work.
- Remaining Phase 0: the test-align cluster (D3-D6, E1-E4, F1-F10) and
  the F8 product-validator CI-env confirmation. Tracked under
  [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
  [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md).
