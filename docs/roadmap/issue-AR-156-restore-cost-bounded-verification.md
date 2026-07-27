---
title: "AR-156: Restore cost-bounded verification feedback"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [testing, ci, performance, cost, developer-experience]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - .github/workflows/ci.yml
  - scripts/select_test_shard.py
  - scripts/pytest_file_timing.py
  - scripts/test_shard_profile.py
  - scripts/run_parallel_change_loop.py
  - scripts/parallel_change_loop_runtime.py
  - scripts/parallel_change_loop_storage.py
  - scripts/prepare_ci_runtime.py
  - tests/test_ci_sharding.py
  - tests/test_doctor.py
  - tests/test_parallel_change_loop.py
  - tests/test_test_shard_profile.py
  - tests/test_release_packaging.py
  - tests/test_smoke_isolation.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-156
priority: p1
tracker_url: null
depends_on: [AR-117]
blocks: []
---

# AR-156: Restore cost-bounded verification feedback

## Problem

A later workflow change removed AR-117's event condition and now runs the
seven-cell full compatibility corpus on every pull-request edit. Local release
verification also has no supported parallel entrypoint, so developers routinely
wait 34-43 minutes for one serial warning-strict corpus and about 69 minutes for
coverage.

## Current state

Successful hosted evidence shows a PR with the deferred matrix used 23.33 raw
runner-minutes and completed in 4m50s, while a comparable current PR used
119.12 raw runner-minutes and completed in 29m19s. The unconditional matrix
alone accounted for 96.27 raw runner-minutes. The current workflow therefore
executes the non-performance corpus collectively under coverage and then seven
additional times per PR, despite AR-117 and the North Star explicitly deferring
the compatibility matrix to `main` or manual dispatch.

Recent hosted runs do not provide code evidence: GitHub rejects their jobs
before any step because account payments failed or the Actions spending limit
must be increased. This external state must not be reported as a test failure
or a green hosted gate.

## Approach

Restore the documented pull-request cadence and make the aggregate quality job
event-aware: pull requests must observe the compatibility job as intentionally
skipped, while `main` and manual runs must observe it as successful. Every other
required dependency remains success-only. Preserve the complete seven-cell
matrix unchanged on its governed events.

Add a cross-platform local runner that uses the same deterministic file
partitioner and one stable, contract-attested, read-only Python runtime. Give
each shard a separate HOME, TEMP, and pytest base directory; execute the exact
warning-strict non-performance corpus in four contained subprocess trees;
retain one coherent bounded head-and-tail log set; and return failure unless
every shard succeeds. The runtime must rebuild safely when its interpreter,
dependency bridge, Node identity, or isolation contract changes. Dry-run must
remain deterministic and filesystem-resource-free. Keep the serial command,
coverage arm, and uninstrumented performance arm as separate canonical release
gates; the parallel runner is the developer change loop, not a weaker release
substitute.

Derive Windows duration weights only from three odd, all-green samples that use
the explicit source-byte partition control. Bind every sample to one clean Git
commit, the exact test and product source, the complete timing harness, runtime
family, worker count, and independently recomputed partition. Exact profiles
must fail closed in strict benchmark mode. During ordinary development, a
profile with unchanged tests, harness, and runtime may remain visibly
`compatible` across product-source edits so the change loop does not discard
its acceleration precisely when it is needed.

## Dependencies

AR-117 and the North Star own the existing hosted cadence. ADR-0030 requires
quantitative claims to use recorded controls rather than inferred speedups.

## Acceptance

- Pull requests require the compatibility job to be intentionally skipped;
  `main` and manual runs require it to succeed.
- No aggregate path accepts cancelled, failed, missing, or unexpectedly skipped
  production gates.
- The seven compatibility cells and all PR coverage, performance, portability,
  artifact, security, documentation, and UI gates remain intact.
- Workflow contract tests pin the exact event/result policy and reject a future
  unconditional compatibility regression.
- The local runner proves serial/sharded test collection equivalence, uses one
  shared attested runtime with a private HOME, TEMP, and base directory per
  shard, aggregates failures, contains cancellation, and cleans up safely.
- Dry-run creates no runtime, lock, venv, Node mirror, receipt, log, or scratch
state; real runs publish one run-bound bounded log set and manifest.
- Opt-in file timing publishes only after every shard is green, binds every
  bounded report to the exact run/shard/exit state, and proves its file union is
  identical to the serial plan before any weight is trusted.
- Versioned timing weights require three distinct, clean, same-commit v2
  artifacts using the independently reproduced source-byte control partition;
  malformed counts, phases, assignments, paths, links, or provenance fail
  closed.
- Automatic loading distinguishes exact, compatible product-drift, stale,
  missing, invalid, disabled, and unsupported profiles. Strict benchmark mode
  accepts exact evidence only.
- Three comparable warm local runs demonstrate at least 30 percent median
  wall-clock improvement before the parallel runner is recommended as the
  default change loop.
- After GitHub billing or spending state is repaired, one PR run and one
  `main` or manual run provide hosted URLs and exact job evidence.

## Implementation evidence

The workflow again skips only the unchanged seven-cell compatibility matrix on
pull requests and requires it to succeed on `push` and manual dispatch. The
aggregate quality job is event-aware and rejects failed, cancelled, missing,
malformed, unexpectedly skipped, or unexpected job results. Every PR coverage,
performance, portability, artifact, security, documentation, and dashboard
gate remains required. The release/workflow contract suite passes 57 tests and
the pinned offline workflow security audit reports no findings.

Comparable successful hosted history shows the governed PR cadence completing
in 4m50s and consuming 23.33 raw runner-minutes. The later unconditional matrix
completed in 29m19s and consumed 119.12 raw runner-minutes, of which the matrix
used 96.27. Restoring the documented cadence therefore avoids 95.79 raw
runner-minutes (80.4 percent) and 24m29s elapsed (83.5 percent) per PR update in
that comparison. These are recorded historical runs, not a claim that current
hosted gates are green: current jobs are rejected before steps by the external
GitHub billing/spending state. The local parallel change loop now uses the
governed four-way file partition, one immutable-contract private runtime,
per-shard state roots, least-privilege environments, explicit process-tree
cancellation, fixed bounded head-and-tail logs, and a run-bound manifest. It
safely rebuilds only an attested Agency-owned runtime when interpreter or Node
identity changes; unknown directory collisions fail closed and remain
untouched. Direct and module dry-runs are byte-identical and leave both the
projected runtime and global-lock parents unchanged.

The author-focused package passes 212 tests with 15 skips; Ruff, format, and
diff checks are green. An independent reviewer passed 211 tests with 15 skips,
the targeted resource-free dry-run regression, an isolated real private-venv
smoke, root-exited descendant cancellation, and a live facade probe that
returned exit 130 with cancellation classified and the child reaped. Fresh-home
direct and module previews were byte-identical, covered all 275 files exactly,
and left the projected runtime, requested runtime home, and global lock parent
unchanged.

Three attempted complete samples are rejected rather than used for a speed
claim. Run `55394bca385e0c9e71205c3b804c7502` completed 3 of 4 shards in
847.171 seconds after its private environment could not rediscover the attested
pytest bridge. Run `4a53ed511c884e37e563e3b56e392e34` completed 3 of 4 in
752.807 seconds, and run `b561e08fea5229da01507f7839f744b8`
completed 2 of 4 in 793.328 seconds; nested Windows self-hosts produced no
output before their deadlines, while one loopback client exhausted an exact
5-second header budget under load. No failed arm is benchmark evidence.

A fourth unchanged sample, `5552d9c9102719741115319ce1e7b223`, completed 3
of 4 shards in 694.726 seconds internally (696.011 seconds wall clock). Its
only failing shard contained eight runner self-host tests whose valid fixtures
inherited the already-long shard pytest root and correctly hit the new
240-character guard. The other shards passed in 436.14, 625.77, and 432.06
seconds; this rejected run is duration telemetry only, not benchmark evidence.
Commit `49aafe1` moves valid fixture homes below the same bounded private root
used by the production self-host while retaining a dedicated over-budget
negative case. The package passes 19 tests in 16.08 seconds normally and 19 in
16.45 seconds from a 195-character outer pytest root.

Run `411b67385c033451c78f632ecc5fc867` is the first valid current-head baseline:
all four shards passed in 676.505 seconds. Pytest shard times were 619.89,
446.28, 578.23, and 508.32 seconds for the exact 275-file union. This is one
correctness baseline, not yet the three-run speed sample. Its 173.61-second
fastest-to-slowest spread also proves source-byte size is a poor Windows weight.

The opt-in `--collect-file-timings` path records bounded setup/call/teardown
nanoseconds for each exact repo-relative file. It maps reports through collected
node IDs so pytest `rootpath` cannot retarget relative arguments, rejects
missing/forged/non-equivalent reports, and publishes no complete artifact for a
failed, timed-out, cancelled, or containment-failed shard. Default execution is
unchanged. Independent review findings were repaired before checkpoint; the
combined runner/sharding/doctor/smoke slice passes 46 tests in 43.87 seconds,
the release-packaging suite passes 57, and Ruff/format/diff checks pass.

The first instrumented attempt, `14c20d874fb2e4287e47f999654af4af`, is also
rejected: it completed 3 of 4 shards in 634.140 seconds after the regression
that verifies repeated plugin configuration temporarily replaced the live
timing state until pytest fixture teardown. The controller correctly recorded
`complete: false` and published no authoritative timing artifact. The test now
uses a nested monkeypatch scope that restores the live state before pytest emits
its own report; the exact test passes alone and all 27 runner tests pass while
being measured by the plugin. The failed attempt is not speed evidence.

Instrumented run `4b5f0f74d963ca4f6582d526fc7a2f7b` then passed all four
shards in 781.945 seconds. Its shard pytest times were 446.48, 393.71, 715.03,
and 435.29 seconds. The artifact identified the dominant Windows files, but its
v1 contract did not bind the product source, clean evidence commit, timing
harness, or exact source-byte assignment. It is retained as diagnostic input
and is not eligible to generate the production profile.

The v2 timing contract now binds all of those inputs, validates every file,
phase, shard, aggregate, and run identity, rejects linked evidence, and
independently reproduces the control assignment before computing medians. It
also revalidates source immediately after shard execution before publishing.
The profile/runner/sharding contract package passes 52 warning-strict tests;
Ruff, format, and diff checks pass. Independent review approved the producer to
loader chain for the three clean source-byte control runs.

Four test-only cost corrections retain the exact exercised contracts while
removing unrelated setup: HTTP fixture shutdown polls at 10 ms, adapter parity
activates only the five asserted agents, preflight concurrency no longer seeds
an unused roster, and delegation tests activate only their asserted agent.
The matched package remained 77 passed with 5 skips and fell from 84.38 to
48.06 seconds, a 36.32-second (43.04 percent) local Windows improvement. This
is a bounded same-machine test-maintenance result, not a full-corpus claim.

The same slice removes accidental test cost without deleting behavior: generic
doctor tests use one active agent and deterministic host/network boundaries;
two equivalent all-host smoke assertions share one real integration run; and
the poisoned-profile isolation test retains one real Hermes hook while stubbing
unrelated hosts. Dedicated suites continue to own inventory and provider probes.

Commit `d2ab19b` binds the dependency bridge to owner-trusted runtime receipts
and records bounded slow-test telemetry. A controlled same-runtime A/B then
isolated Windows path geometry: a short root passed in 2.47 seconds, while the
long-root arm reached 180 seconds without stdout or stderr. Commit `7d11313`
therefore keeps the 60-second child bound, rejects critical runtime paths above
240 characters, allocates nested self-hosts below a short private root, and
proves the real runner and worker PIDs are reaped during crash recovery. The
focused package passes 20 tests in 16.11 seconds; both private-runtime self-host
tests pass in 7.96 seconds even with a deliberately long outer temp path.
Because v2 changes the governed evidence contract and adds one profile test
file, three new clean source-byte control samples, matched exact-weight samples,
and a one-shard control remain before the local runner acceptance can close.
The canonical serial, coverage, and performance gates remain required.
