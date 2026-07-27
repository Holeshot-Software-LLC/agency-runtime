---
title: "AR-156: Restore cost-bounded verification feedback"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [testing, ci, performance, cost, developer-experience]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - .github/workflows/ci.yml
  - scripts/select_test_shard.py
  - scripts/pytest_file_timing.py
  - scripts/test_shard_profile.py
  - scripts/test_shard_weights/windows-cpython313-v1.json
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
depends_on: [AR-117, AR-158]
blocks: [AR-159]
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
required dependency remains success-only. Gate expensive roots behind fast
same-revision quality. Preserve serial compatibility on Ubuntu/Python 3.10,
3.11, 3.12, and 3.14 and Windows 3.10 and 3.14; preserve the exact Python 3.13
non-performance union through four coverage shards and retain uninstrumented
Python 3.13 performance.

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
- Six serial compatibility cells, four exact Python 3.13 coverage shards, and
  all PR performance, portability, artifact, security, documentation, and UI
  gates remain intact. The accepted serial-versus-sharded non-equivalence is
  explicit in ADR-0097.
- Fast dependency, static, workflow, and UI checks cover the same PR merge
  revision as downstream jobs before expensive fanout. History-derived ledgers
  deliberately re-check out the complete durable head.
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
- Opt-in timing-profile loading distinguishes exact, compatible product-drift,
  stale, missing, invalid, disabled, and unsupported profiles. The public
  loader, plan API, and CLI default to source-byte weights; strict benchmark
  mode requires explicit `auto` selection and accepts exact evidence only.
- Three comparable warm four-worker runs plus one same-commit one-worker
  control demonstrate at least 30 percent median wall-clock improvement before
  the parallel runner is recommended as the default change loop. Automatic
  timing-profile promotion separately requires 30 percent median improvement
  over the four-worker source-byte control.
- After GitHub billing or spending state is repaired, one PR run and one
  `main` or manual run provide hosted URLs and exact job evidence.

## Implementation evidence

The workflow skips the compatibility matrix on pull requests and requires it to
succeed on `push` and manual dispatch. Fast same-revision quality gates every
expensive CI root and performs `pip check`, Ruff, formatting, whitespace,
workflow contracts, and dashboard UI coverage before fanout. It then checks out
the complete durable head solely for documentation ledgers. The aggregate is
event-aware and rejects failed, cancelled, missing, malformed, unexpectedly
skipped, or unexpected dependency results. Six serial compatibility cells,
four Python 3.13 coverage shards, performance, portability, artifacts, security,
documentation, and dashboard gates remain. ADR-0097 records that sharded Python
3.13 execution does not reproduce one serial process's ordering or session
fixture lifetime.

The exact sharding/workflow contract package passes 64 tests. Ruff and format
checks pass, documentation validation covers 414 maintained Markdown files,
and pinned `zizmor 1.26.1` reports no workflow finding in strict offline mode.

Comparable successful hosted history shows the governed PR cadence completing
in 4m50s and consuming 23.33 raw runner-minutes. The later unconditional matrix
completed in 29m19s and consumed 119.12 raw runner-minutes, of which the matrix
used 96.27. Restoring the documented cadence therefore avoids 95.79 raw
runner-minutes (80.4 percent) and 24m29s elapsed (83.5 percent) per PR update in
that comparison. These are recorded historical runs, not a claim that current
hosted gates are green: current jobs are rejected before steps by the external
GitHub billing/spending state. Removing the redundant Ubuntu/Python 3.13 serial
cell is estimated from comparable history to avoid another 7.30-10.90 raw
runner-minutes on `main` or manual runs; quality-first short-circuit savings vary
with the failure and are not counted as guaranteed savings. The local parallel
change loop now uses the
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

Two clean v2 controls passed all four shards: run
`e688daea27910329dd1b21604ff68298` took 690.599 seconds and run
`7c310844fb167f0fc2263a9cdd6e9b32` took 710.037 seconds. Their byte-balanced
shards ranged from 278.89 to 652.58 seconds. The third attempt,
`2c655b34b1e22d55a42b52db93c491f3`, is rejected at 3/4: a legitimate slow
Store observation preceded the MCP observation and exposed AR-158's ambiguous
first-record test selector. No complete artifact was published. Because the
test fix changes the exact corpus content, the first two artifacts remain valid
diagnostics but cannot be mixed into the replacement profile's three samples.

The replacement v2 controls all passed 4/4 from clean ledger commit `a34a9dc`:
`b32973e5f8cf0a9d018b8304e6059fc1` took 639.984 seconds,
`c3b5e80765eab687f104306781a7c79e` took 657.689 seconds, and
`aebb1f7dacf7eb250e3da45e050af9cd` took 639.573 seconds. Their
controller-wall median is 639.984 seconds. Every artifact contains the exact
276-file union, 7,804 collected tests, clean commit identity, and the same
source-byte assignment.

The generator accepted only those three artifacts and wrote the versioned
Windows CPython 3.13 profile with SHA-256
`5415fc292a6b542bfd5491f183f177f95f57997636eacaa868dca3536489b4f3`.
Strict dry-run loads it as `duration-lpt-v1/exact` and assigns 68, 69, 70, and
69 files. The planned median-duration totals differ by only 7.4801 ms across
shards; that is schedule input evidence, not a wall-time speed claim. Matched
strict-profile runs and the one-worker control are now complete.

Three strict-profile runs passed the same 7,804-item, 276-file corpus at frozen
manifest wall times of 576.350, 575.973, and 575.949 seconds; their median is
575.973 seconds. Compared with the 639.948-second four-worker source-byte
median, duration weighting saved 63.975 seconds, or 9.997 percent. That misses
the unchanged 30-percent automatic-promotion gate. The profile remains valid
explicit opt-in evidence, while the public loader, plan API, and CLI default to
`source-bytes`; strict reproduction explicitly combines `--partition auto`
with `--require-exact-shard-weights`.

The same clean checkpoint passed one instrumented one-worker source-byte
control, run `6089116690329584d1763e19869c65a8`, in 2,253.785 seconds. The
four-worker strict-profile median therefore reduced developer wall time by
74.444 percent, a measured 3.913x speedup, while preserving the exact file union
and warning-strict corpus. This clears the parallel-runner threshold without
promoting the under-threshold timing profile by default.

Artifact analysis shows the exact assignment is already within about nine
seconds of its measured four-way phase-work floor. The next material local
speed work must reduce total fixture, Store, and cleanup cost rather than
reshuffle files: per-test offline-config writes, repeated validated SQLite
connections inside composite operations, and the 22-25 second synchronous
scratch-publication tail are the leading measured candidates.

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
The v2 controls, matched exact-weight samples, and one-shard control now close
the local runner's speed-evidence gate. The timing profile remains opt-in
because its separate promotion gate failed. Current-head canonical coverage,
performance, artifact, and hosted evidence remain required before AR-156 can
close.
