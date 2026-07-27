---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-27
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 85549a4d8000aef708b7e1b90e3bcfb90a7d81b1
minimum_ledger_commit: 0001bf77acfef4092e8ac21582375790f1b68061
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
- Telemetry reported 62.0 percent remaining. The clean `85549a4`/`0001bf7`
  measured-profile pair precedes the completed speed comparison.
- Security, optimization, and UI-to-Store traceability findings AR-128 through
  AR-155 have governed local repairs or explicit remaining evidence gates.
- AR-156 now has three clean v2 source-byte controls, three matched strict
  timing-profile runs, and one same-commit one-worker control. Parallelism
  clears its gate; automatic timing-profile promotion does not.

## completed-evidence

- Pre-final integrated runs reached 7,604 passed, 61 skipped, and 1 expected
  failure in 34m20s; coverage passed 97.08 percent and performance passed.
  None is current-head final evidence after the runner changes.
- Dashboard trace repairs AR-149 through AR-155 are committed. Source UI tests
  pass 101 cases at 98.61 percent lines, 91.06 percent branches, and 97.90
  percent functions. Packaged assets are 258,787 bytes against the unchanged
  263,168-byte cap, leaving 4,381 bytes of headroom.
- Packaged-contractor lookup now batches nine trusted reads into one. The local
  Windows warm install median fell from 160.340 ms to 28.712 ms; the stable
  snapshot median fell from 539.410 ms to 408.184 ms. This is local evidence,
  not a cross-platform claim.
- Pull requests defer compatibility to `main` or manual dispatch. Same-revision
  fast quality now gates expensive fanout; six serial cells plus four exact
  Python 3.13 coverage shards retain the governed surfaces. Historical PR
  comparison avoids 95.79 raw runner-minutes; hosted jobs remain billing-blocked.
- AR-156 uses the governed four-way 276-file partition, one contract-attested
  private runtime, per-shard HOME/TEMP/basetemp, least-privilege environments,
  contained cancellation, bounded head-and-tail logs, and one run manifest.
  Unknown runtime collisions fail closed; attested stale runtimes self-heal.
- Rejected runs found and repaired receipt, long-path, disconnect, fixture,
  timing-self-measurement, and multi-surface observation defects. None was
  admitted as benchmark evidence.
- The v2 producer, validator, generator, and loader bind a clean Git commit,
  product/test/harness digests, runtime identity, exact source-byte assignment,
  file/phase/shard aggregates, and post-run source revalidation. The focused
  contract package passes 52 tests and independent review approved clean runs.
- Four behavior-preserving test setup reductions kept 77 passes and 5 skips
  while a matched local Windows slice fell from 84.38 to 48.06 seconds
  (43.04 percent). This bounded slice is separate from the full-corpus evidence.
- Replacement controls have a 639.948-second frozen-manifest median. Three
  strict-profile runs have a 575.973-second median: a stable 9.997-percent gain
  that misses the unchanged 30-percent automatic-promotion gate. Source bytes
  are the public default; `--partition auto` is explicit opt-in.
- One worker passed the same corpus in 2,253.785 seconds. Four workers reduce
  wall time by 74.444 percent (3.913x), clearing the local parallel-loop gate.
  Rebalancing is near its phase-work floor; fixture, Store, and cleanup cost are
  the next measured targets.
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
- AR-156 still needs current-head canonical and hosted evidence. GitHub billing
  blocks hosted jobs, and `main` currently has neither branch protection nor a
  repository ruleset; changing hosted enforcement requires authorization.
- AR-119/AR-125 still lack a benchmark-valid outcome corpus and current-artifact
  host/OS evidence. Malformed, timed-out, or unknown upstream arms remain
  invalid, never losses.
- GitHub billing/spending state blocks hosted evidence. Tracker creation or
  closure and all other outward actions remain unauthorized.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. After this
clean checkpoint, continue the same persistent goal through normal compaction.

## next-bounded-work-package

1. Enforce source-byte default selection and record the completed speed evidence.
2. Gate expensive Actions fan-out behind same-revision fast quality, retain the
   governed compatibility/coverage surfaces, and record hosted-enforcement risk.
3. Remove measured per-test fixture and cleanup cost without weakening gates.
4. Implement AR-143 through a prepare-verify-revalidate-commit seam, beginning
   with roster rollback, and keep every unmigrated positive mutation blocked.
5. Run current-head canonical coverage, performance, docs, UI, security,
   artifact, and isolated-install gates.
6. Reinstall the reviewed artifact, dogfood routing/roster/hiring,
   and report Agency activation only from exact receipts.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m scripts.run_parallel_change_loop --dry-run
python -m scripts.run_parallel_change_loop
python -m scripts.run_parallel_change_loop --partition auto --require-exact-shard-weights --dry-run
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
