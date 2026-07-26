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
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 49aafe1a148d5b34faebe894e71ccaa74351350d
minimum_ledger_commit: c89c36528afec88202b4df771a63dfc9f8b8faf5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the production-readiness push. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) owns the full
acceptance contract; this capsule records only the active checkpoint.

## checkpoint

- Main is locally ahead of `origin/main`; no push, PR, tracker mutation, tag,
  publication, or release was authorized.
- The user-owned untracked `docs/analysis/2026-07-25-deep-audit-findings.md`
  remains unchanged and excluded from every commit.
- Telemetry reported 85.8 percent remaining after normal compaction. The clean
  `49aafe1`/`c89c365` bounded-test-home repair-and-ledger pair precedes this
  checkpoint.
- Security, optimization, and UI-to-Store traceability findings AR-128 through
  AR-155 have governed local repairs or explicit remaining evidence gates.
- AR-156's self-host path cause is repaired and focused evidence is green.
  Complete timing has started, but every sample so far is explicitly invalid;
  no local speed claim has been made.

## completed-evidence

- Three ordinary integrated Python runs culminated in 7,522 passed, 61 skipped,
  and 1 expected failure in 42m43s. A later pre-final-trace run passed 7,604
  with 61 skips and 1 expected failure in 34m20s. Neither is current-head final
  evidence after the latest runner changes.
- The exact pre-final-trace coverage arm passed 97.08 percent against the
  unchanged 97 percent floor; the separate three-test performance arm passed.
  Both require current-head confirmation.
- Dashboard trace repairs AR-149 through AR-155 are committed. Source UI tests
  pass 101 cases at 98.61 percent lines, 91.06 percent branches, and 97.90
  percent functions. Packaged assets are 258,787 bytes against the unchanged
  263,168-byte cap, leaving 4,381 bytes of headroom.
- Packaged-contractor lookup now batches nine trusted reads into one. The local
  Windows warm install median fell from 160.340 ms to 28.712 ms; the stable
  snapshot median fell from 539.410 ms to 408.184 ms. This is local evidence,
  not a cross-platform claim.
- Pull requests again defer the unchanged seven-cell compatibility matrix to
  `main` or manual dispatch. Historical comparison avoids 95.79 raw
  runner-minutes and 24m29s elapsed per PR update; current hosted jobs are
  blocked before steps by GitHub billing/spending state.
- AR-156 uses the governed four-way 274-file partition, one contract-attested
  private runtime, per-shard HOME/TEMP/basetemp, least-privilege environments,
  contained cancellation, bounded head-and-tail logs, and one run manifest.
  Unknown runtime collisions fail closed; attested stale runtimes self-heal.
- Runtime-contract v2 restores nested pytest only from exact owner-trusted
  receipts. Four complete attempts remain rejected: 3/4 in 847.171 seconds,
  3/4 in 752.807 seconds, 2/4 in 793.328 seconds, and 3/4 in 694.726 seconds.
  They found one receipt defect, one Windows path hang, one overloaded
  loopback deadline, and one long test-fixture root; none is speed evidence.
- A same-runtime A/B passed under a short root in 2.47 seconds and timed out
  under the long root at 180 seconds with no output. The runner now rejects
  critical Windows paths above 240 characters and keeps nested homes short.
  Focused evidence is 20 passes in 16.11 seconds and both real private-runtime
  self-hosts pass in 7.96 seconds with a long outer pytest path. Crash recovery
  verifies both the real runner and child PIDs are gone before reuse.
- Commit `49aafe1` keeps valid runner-test homes below the Windows path ceiling.
  The runner package passes 19 tests in 16.08 seconds normally and 19 in 16.45
  seconds from a deliberately 195-character outer pytest root.
- Fresh source status sees all five hosts and the configured provider. The
  globally installed `agency` CLI is stale: it omits ZCode from status help and
  rejects the current provider configuration. The Store has 0 specialist-load
  receipts and 0 model receipts, so current manual subagents are not claimed as
  Agency-selected specialists.
- AR-157's shared public/dashboard disconnect boundary is implemented in
  `12640d0`; the focused package passes 154 tests with 3 skips. Current-head
  coverage and warning-strict release gates remain before closure.

## exact-blocker

- AR-143 still has no production OS-backed operator-presence backend. Microsoft
  documents a genuine Windows desktop path only from build 22000 using
  `IUserConsentVerifierInterop` and an active app-owned HWND; it is not yet
  implemented or human-canaried. A console/pseudoconsole HWND is insufficient.
- Linux positive persistent mutations remain unsupported until a separately
  governed non-exporting OS backend exists. macOS is not an advertised surface.
- The shared AR-143 guard binds and rechecks only the parsed namespace. It does
  not prepare the authoritative mutation or bind Store identity, resolved
  target state, and generation through the committing transaction.
- Its native prompt exposes only command, family, and opaque digest; it does not
  yet show the resolved state transition and consequence required for informed
  human co-authorization.
- Positional low-entropy secrets enter an unkeyed deterministic digest, while
  deferred stdin/prompt values are read after the guard. The positive redesign
  must prepare deferred values and avoid exporting a secret-guessing oracle.
- A no-UI Windows activation-factory probe succeeded, but the reviewed ctypes
  draft was rejected before commit: callback pins could be released while
  native code retained them, and timeout cleanup could close a running async
  operation. Positive mutations remain disabled.
- Persistent fresh installation remains fail-closed behind AR-143. Normal
  Codex hook trust also requires user-owned terminal-TUI review; neither may be
  bypassed while the user is remote.
- AR-156 still needs three green comparable warm four-shard timings plus a
  matched one-shard control proving at least 30 percent median wall-clock
  improvement. The canonical current-head serial, coverage, performance, docs,
  UI, artifact, and installed smoke gates remain separate requirements.
- AR-119/AR-125 still lack a benchmark-valid outcome corpus and current-artifact
  host/OS evidence. Malformed, timed-out, or unknown upstream arms remain
  invalid, never losses.
- GitHub billing/spending state blocks hosted evidence. Tracker creation or
  closure and all other outward actions remain unauthorized.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. After this
clean checkpoint, continue the same persistent goal through normal compaction.

## next-bounded-work-package

1. Run an unchanged full parallel corpus; preserve its run-bound logs and reject
   any non-green sample rather than changing the gate after observing it.
2. Run three green comparable warm parallel corpora plus a matched one-shard
   control; do not change the gate after observing.
3. Use the recorded duration output to rebalance only if exact file coverage,
   isolation, and release gates remain unchanged.
4. Run current-head canonical serial, four-way exact coverage, performance,
   docs, UI, security, artifact, and isolated-install gates.
5. Implement AR-143 through a prepare-verify-revalidate-commit seam, beginning
   with roster rollback, and keep every unmigrated positive mutation blocked.
6. Reinstall the reviewed artifact in isolation, dogfood routing/roster/hiring,
   and report Agency activation only from exact receipts.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m scripts.run_parallel_change_loop --dry-run
python -m scripts.run_parallel_change_loop
python -m pytest tests -q -W error
python -m pytest tests -q -W error -p no:cacheprovider -m performance
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/verify_docs.py
git diff --check
~~~

## constraints

- Telemetry immediately before every live evaluation, benchmark corpus, or
  canary; ensure a clean checkpoint when it is at or below 50 percent.
- Preserve the fixed 15,000 ms cold and one-call fast AR-119 controls. Never
  weaken coverage, parser, authority, timing, or asset thresholds after results.
- Do not claim Agency superiority, activation, specialist loading, model
  receipt, delegation, contractor hire, or host canary without exact evidence.
- Do not delete or modify unknown/unattested paths. Preserve the user draft.
- No push, PR, hosted dispatch, publication, tracker mutation, tag, release, or
  trust-store action without explicit outward authorization.
