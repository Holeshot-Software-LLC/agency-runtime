---
title: "AR-140 current performance disposition"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [performance, backlog, evidence, linux]
related:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/roadmap/acceptance/evidence/AR-140-linux-routing-20260907.json
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-140 current performance disposition

## Outcome and limits

The implementation is present; retain the original isolated-supported-runner
obligation, with Windows reserved for the owner. No code or threshold changes
are needed by these current local observations. No criterion is checked or
judged here, and no duplicate legacy tracker is created.

Review checkpoint: 82fb202882fe973d9120d070eb64db66d29ecc86. Product source:
1ada216c208777630ec7162acf5a390f420fc0a4 (merged PR #700). The difference is only
the preceding merge's worklog/reciprocal ledger. Python 3.12.3, local x86-64 Linux
7.0.0-29, glibc 2.39. The command ran alone before the focused tests, without
parallel agent work; this is not an isolated hosted runner or cross-platform
certification.

ADR-0121 keeps deterministic candidate recall separate from selection.
The complete-cache-path fixture seeds a synthetic inference receipt and
validates reuse, trace freshness and exact configuration/roster identity.
It does not call a provider, hire a worker, spawn a host child, or measure a
fresh staffing decision. AR-253 owns that latency/quality/delivery outcome.
A 16.989 ms version command is not a 16.989 ms initialized staffing turn.

## Existing source boundaries

- `agency_runtime/core/selector/semantic_retrieval.py`: bounded immutable
  sparse indexes, exact-revision/content keys, identity collision rejection,
  support postings and smaller-vector cosine. No deterministic staffing.
- `agency_runtime/core/selector/cache.py` and `pipeline.py`: detached
  cache copies, mutation-sensitive roster/config/policy fingerprints and
  host/capability/workforce generation binding.
- `agency_runtime/core/routing_snapshot.py`: reuse only after the trusted
  generation still agrees; a changed generation causes recapture.
- `agency_runtime/core/workforce/known_contractors.py`: bounded batched worker
  snapshot; tests retain parameter binding and concurrent-conflict rejection.
- The frozen workforce contract's canonical-byte cache stays bounded at 512
  and rejects changed keys; the CLI module still uses the lazy dispatcher.
- `agency_runtime/core/evals/benchmarks.py`: explicit three-tier time/memory
  budgets, five warm samples per tier, five cache batches and seven fresh
  CLI processes. No sample, gate, exclusion or runtime source changed.

## Exact current checks

The complete raw result, including every reported sample, hash and gate, is
[the JSON receipt](AR-140-linux-routing-20260907.json), observed at
2026-09-07T05:30:46.902290Z. All 39 gates pass.

The command uses the same `run_routing_eval(include_details=False)` entry
used by `agency eval routing --json --no-details`, with `PYTHONPATH=.`
and the current dev interpreter. It prints the untouched report plus
observation time, Python and platform metadata. Providers are disabled by
the benchmark fixture; no user configuration or credential was changed.

| Probe | Current local result | Unchanged budget |
|---|---|---|
| 1,000-row narrowing p95 | 1.081 ms | 20 ms |
| Complete-cache-path p95 | 0.201 ms, 640 samples | 2 ms |
| Concurrent narrowing | 145.75 calls/s, eight synchronized workers | 40 calls/s, overlap at least two |
| 263-row retrieval | 107.875 ms cold / 2.235 ms warm p95 / 6.317 MiB | 1,500 ms / 15 ms / 16 MiB |
| 1,000-row retrieval | 333.794 ms / 21.479 ms / 19.007 MiB | 5,000 ms / 40 ms / 64 MiB |
| 10,000-row retrieval | 2,946.580 ms / 193.862 ms / 167.830 MiB | 20,000 ms / 300 ms / 256 MiB |
| Fresh CLI version process | 16.989 ms p50 / 19.129 ms p95 | 250 ms p50 |

Cold retrieval includes tracemalloc overhead. Warm p95 is nearest-rank over
five samples, not a broad statistical latency claim. The 10,000-row first warm
sample is 193.862 ms; all five remain in the receipt rather than discarding it.
The result hash remains
`9214506c8a46c50e1cff4b2e0793127935c10f8f092d5a8597c8623cf4f69f60`.
Required candidate recall, case recall and top-one relevance are 1.0;
precision at three is 0.6364 against its 0.60 floor, not perfect precision.
Forbidden rate is zero. Policy macro F1 is 0.9958; all delegation metrics are 1.0.

Focused warning-strict commands, each with `PYTHONPATH=.`:

```bash
python -m pytest tests/test_semantic_retrieval.py tests/test_routing_correctness.py \
  tests/test_routing_snapshot.py tests/test_known_contractor_install.py \
  tests/test_roster_snapshot_generation.py tests/test_routing_eval_suite.py \
  -m 'not performance' -q -W error
python -m pytest tests/test_selector_cache_hot_path.py tests/test_workforce_contract.py \
  tests/test_selector_coverage_complete_basics.py -q -W error
```

Results: 135 passed, two performance tests deselected (20.04s); 67 passed
(1.48s). The separate complete routing evaluation above exercises the published
performance checks. Pure-data eligibility fixtures may contain a Windows
platform string; no native Windows execution is claimed.

The preceding AR-138 package's named spine (1085 pass/three existing skips),
172 UI passes and 184/184 decision-conformance kills remain scoped prior
receipts, not newly run here. A clean
`git diff --exit-code 2ecde1a5 HEAD -- agency_runtime tests scripts`
proves those product/test/script bytes unchanged at this review checkpoint.
The full corpus, coverage/interpreter matrix, workflow dispatch, provider calls
and installed-native canaries were not run for this documentation disposition.

## Next action

Keep AR-140 open until its pinned, isolated supported-runner evidence exists,
including the owner's Windows arm, then use the normal isolated acceptance
gate. Current local passing numbers neither waive that requirement nor imply
the separate staffing-latency backlog is complete. Proceed to the next oldest
unfinished non-Windows record after publishing this disposition.
