---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-26
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-144-restore-dashboard-ui-release-coverage.md
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-146-repair-dashboard-collection-cursor-validation.md
  - docs/roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 093241033300da2347baa898728ef89f6f5df92f
minimum_ledger_commit: 4d15b2befc667c4a704623157432867ab137db4f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for AR-119. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) owns the full
acceptance contract. ADR-0087 governs configured inference; ADR-0088 governs
the deterministic typed-recall floor only when inference is not configured.

## checkpoint

- Main is locally ahead of origin/main at 5001d78 by the governed audit,
  checkpoint, Waves 1 and 2, and ledger commits. No push, PR, or tracker mutation was
  authorized.
- The pre-existing untracked 2026-07-25 deep-audit draft is preserved unchanged
  and excluded from commits.
- Telemetry reported 34.6 percent remaining; the clean 0932410/4d15b2b pair
  satisfies the required hard checkpoint before live evaluation.
- The current package integrates AR-133 through AR-148 source work plus the
  AR-140/AR-141 performance and compatibility slice.
- The first complete post-checkpoint Python arm ran 43m39s and failed 34 tests.
  Its exact owning 12-module reproducer now passes 424 tests in 70.71 seconds.
- The second complete arm ran 43m27s: 7,521 passed, 61 skipped, 1 expected
  failure, and 1 failed because a legacy injected wizard fixture omitted
  ZCode. The canonical five-host fixture was repaired.
- The third complete arm is green: 7,522 passed, 61 skipped, and 1 expected
  failure in 42m43s. It is the authoritative current integrated Python result.

## completed-evidence

- The initial fresh Codex install from source preserved nine contractors,
  registered and enabled Codex, started the owner dashboard, and remained
  activation-required for normal-profile hook trust. That installation
  predates the current source changes.
- Wave 1 made MCP/broker control read-only, isolated subprocess environments,
  revalidated Store trust, repaired MCP contracts and deterministic safe-gap
  hiring, enforced schema 36, and restored the fixed asset budget.
- Finalization now validates and commits one complete bounded batch atomically.
- Schema 37 persists expiring single-use native-child scopes; separate parent
  and child hook subprocess tests prove exact correlation, replay denial, and
  planned-work fail-closed behavior.
- ZCode now has an independent exact seven-event configuration, atomic
  merge/rollback, status, toggle, hook, lineage, and smoke source contract.
- Dashboard collections expose cursors, exact totals, revisions, and declared
  live semantics. One coherent control snapshot is stage-validated before
  commit; stale generations cannot overwrite newer state; focus and selection
  survive refresh; safe request IDs are visible.
- Content-free observations correlate dashboard, HTTP, MCP, hooks, and
  slow/error Store work without prompt, token, SQL, exception-message, or path
  fields. Hiring outcomes are present in normalized route receipts.
- Revision-aware retrieval and both lazy CLI version entrypoints preserve
  correctness hashes; `python -m` fell from about 647 ms to 112 ms. At 10,000
  agents cold/warm-p95/peak were 8,817.588 ms, 84.193 ms, and
  189.589 MiB. These are local controls, not general superiority evidence.
- A later mixed-suite arm exposed insufficient cached-routing margin at
  2.103 ms. Eligibility now supplies an opaque proof after its detached
  full-roster comparison so fingerprinting does not immediately repeat that
  scan. Five unchanged final-source controls produced deterministic median
  p95 values of 1.345, 1.448, 1.318, 1.442, and 1.745 ms without changing
  the 2.0 ms gate.
- The complete run exposed a real ZCode wizard omission; the canonical
  five-host detection/status list now includes ZCode. Dashboard request
  handling also tolerates pre-header disconnects, authenticates before
  evaluating broker scope, and records expected disconnect degradation.
- Deprecated route/header compatibility wrappers and canonical identity,
  bounded-value, filesystem-trust, and executable helpers are restored.
- Schema currentness now rejects weakened activation-ledger constraints,
  same-name workforce authority triggers, and quoted-literal drift. Malformed
  HMAC text returns invalid authority. Focused tests pass 58; the broader
  Store/schema/roster/workforce package passes 434 with 2 skips.
- Explicit 263- and 1,001-worker dashboard paging drains every row and exact
  facet. A committed inter-page insert appears once in stable key order.
- The exact 12-module integration arm that owned all 34 complete-run failures
  now passes 424 tests. Focused routing/dashboard correctness passes 79 tests
  and the unchanged production microbenchmark passes independently.
- Both wizard coverage modules pass 36 tests with the canonical five-host
  detection fixture.
- The complete `python -m pytest tests/ -q -W error` gate passes 7,522 tests
  with 61 skips and 1 expected failure.
- The exact dashboard release-coverage command passes all 84 tests at 97.13
  percent lines, 91.28 percent branches, and 96.32 percent functions without a
  threshold or production-code change.
- The first exact Python coverage arm failed four tests and the fixed 97
  percent floor at 96.66 percent after 57m35s. Focused deterministic repairs
  pass 33 tests; matched Store/MCP coverage adds 177 statements and closes 38
  partial branches, while focused dashboard coverage adds 87 statements.
- AR-146 repairs generated cursor validation; 29 dashboard server and 12
  cursor/activity/observation tests pass.
- AR-147 replaces flat Windows ACE extraction after a native-valid nested
  conditional foreign full-control grant bypassed directory and executable
  trust classification. The repaired focused security suite passes 402 tests
  with 6 skips; integrated release evidence remains pending.

## exact-blocker

- AR-143 has no production OS-backed, non-exporting operator-presence verifier.
  Dashboard and model-facing paths are read-only and real CLI mutations fail
  closed. Do not bypass this with static confirmation, credentials, mocks, or a
  model-callable capability.
- Because install is a persistent mutation, the current source cannot be
  freshly installed or canaried autonomously until AR-143 has a genuine
  human-presence backend. The earlier installation is not current-source proof.
- Normal-profile Codex activation still requires user-owned terminal-TUI hook
  review. No trust store may be read or changed by this task.
- AR-138 needs fresh post-install desktop/mobile accessibility QA. AR-137 and
  AR-144 are locally acceptance-complete but lack authorized tracker actions.
- AR-119 and AR-125 still lack a benchmark-valid completed value corpus and
  current production-candidate evidence across claimed host/OS surfaces.
  Malformed or timed-out upstream arms remain invalid, never losses.
- AR-145 still requires the exact aggregate 97 percent coverage rerun and
  separate uninstrumented performance suite.
- Tracker creation/closure, push, PR, hosted checks, tags, publication, and
  release remain unauthorized outward actions.

## same-task-continuity

Context thresholds never create, fork, transfer, or stop this task. After this
clean checkpoint, continue the same persistent goal through normal compaction.

## next-bounded-work-package

1. Run routing, exact Python coverage, performance, and full release gates.
2. Finish safe AR-140/AR-141 work only from reproduced general evidence.
3. Build isolated artifacts and smoke every mutation-free current-source path.
4. Keep real install and AR-125 claims behind their exact authority/evidence.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/ -q -W error
python -m pytest focused split packages -q -W error
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
python -m pytest tests/test_distribution_verifier_hardening.py tests/test_release_packaging.py -q -W error
ruff check and format check
python scripts/verify_docs.py
git diff --check
~~~

## constraints

- Telemetry immediately before every live evaluation or canary.
- Never weaken typed coverage/parser validation, add scenario routes, increase
  the fixed 15000 ms cold or one-call fast budgets after observing results, or
  reinterpret malformed upstream output.
- Do not claim Agency superiority without a benchmark-valid measured corpus.
- Do not claim native loading, a model receipt, specialist load, delegation,
  contractor hire, or host canary without exact corresponding evidence.
- No push, PR, hosted Actions, publication, tracker creation/edit/closure, tag,
  or release without explicit outward-action authorization.
