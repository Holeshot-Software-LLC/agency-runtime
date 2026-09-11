---
title: "AR-440 acceptance verification record"
status: active
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [acceptance, hooks, runtime-staleness]
related:
  - docs/roadmap/issue-AR-440-a-stale-hook-runtime-blocks-every-turn-without-naming-itself.md
  - docs/decisions/0253-name-the-stale-hook-runtime-when-a-turn-cannot-be-verified.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-440
candidate_commit: 13d567d14b67e0089b5abaefe0cb57d55628b7a3
evidence_cutoff: 2026-09-11
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/878
---

# AR-440 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the hook
boundary's reaction to a runtime drift (ADR-0253) and two bounded
executions on the owner machine after the PR #883 reinstall. No newer
projection has been installed since that reinstall, so the third criterion's
two halves are cited separately: the drift read from inside a real stale
projection against the real launcher pointer, and the installed hook's
reaction against a scratch pointer with a configuration key it does not
know. The scratch executions never touched the live store.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Drift read inside the guarded try; the reason names both digest prefixes, the sanitised failure class and the restart; the stderr suffix | 2026-09-11 | agency_runtime/adapters/hooks.py:134-180 |
| 1 | file | The Stop path picks the stale reason when drift is present and the generic reason otherwise, in the retry or block shape by host | 2026-09-11 | agency_runtime/adapters/hooks.py:380-392 |
| 1 | file | Both boundary handlers read the drift after a failure and print it on stderr | 2026-09-11 | agency_runtime/adapters/hooks.py:3748-3792 |
| 1 | test | Stale Stop on claude names both projections, the failure class and the restart with no exception message; zcode keeps the block shape; no drift keeps the generic reason; a failing import still blocks with the generic reason; the reason is bounded and sanitised | 2026-09-11 | tests/test_stale_hook_runtime.py:77-180 |
| 1 | command-output | Focused regressions pass | 2026-09-11 | docs/roadmap/evidence/AR-440-focused-tests-20260911.txt:1-8 |
| 2 | file | The prompt-hook boundary still publishes and its log entry carries the drift | 2026-09-11 | agency_runtime/adapters/hooks.py:322-351 |
| 2 | test | A stale prompt hook publishes `{}` and its stderr line and log record name the drift beside the cause | 2026-09-11 | tests/test_stale_hook_runtime.py:114-131 |
| 2 | command-output | Focused regressions pass | 2026-09-11 | docs/roadmap/evidence/AR-440-focused-tests-20260911.txt:1-8 |
| 2 | command-output | Named fast spine with the hook suites passes on the merged tip | 2026-09-11 | docs/roadmap/evidence/AR-440-fast-spine-20260911.txt:18-18 |
| 2 | command-output | Decision conformance kills all 188 mutations on the merged tip | 2026-09-11 | docs/roadmap/evidence/AR-440-decision-conformance-20260911.json:1-13 |
| 3 | file | The stale projection this session loaded reports drift against the real pointer from inside its own process | 2026-09-11 | docs/roadmap/evidence/AR-440-stale-hook-proof-20260911.json:6-12 |
| 3 | file | The installed hook, with a scratch pointer naming another projection and an unknown configuration key, rejects the Stop naming both digest prefixes and the failure class and prints the drift on stderr | 2026-09-11 | docs/roadmap/evidence/AR-440-stale-hook-proof-20260911.json:13-24 |
| 3 | file | The previous projection's reaction to the same failure: the generic reason and only the exception class on stderr | 2026-09-11 | docs/roadmap/evidence/AR-440-stale-hook-proof-20260911.json:25-32 |
| 3 | file | Findings and limits, including that no newer projection has been installed since | 2026-09-11 | docs/roadmap/evidence/AR-440-stale-hook-proof-20260911.json:33-39 |
| 3 | tracker | Tracker issue for parity | 2026-09-11 | https://github.com/Holeshot-Software-LLC/agency-runtime/issues/878 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-440.1-20260911-d9340a1f` | `7d502a5c4ea1f8129cd80bd2e7c1346c38269a4fed77fcdb6daba51bf7b9c981` | 2026-09-11 | hooks.py:151-167 builds a Stop reason naming both digest prefixes, the sanitised failure class and the restart; hooks.py:381-390 uses it only when drift exists (else generic) with retry=host!="zcode", so retry for claude/codex and block for zcode; tests 77-111 assert all four and pass. |
| 2 | satisfied | `AR-440.2-20260911-ff421af4` | `e77350f0d871b36e63bc26bf362b438d0bca2f3c77c3bd1917d89c221ca3c1d5` | 2026-09-11 | hooks.py:321-350 returns {} for UserPromptSubmit with a preflight_unavailable log carrying stale_runtime, hooks.py:3761-3769 prints the drift on stderr, tests/test_stale_hook_runtime.py:114-131 pins both, and the focused (7 passed), fast spine (1253 passed) and conformance artifacts pass. |
| 3 | satisfied | `AR-440.3-20260911-d6e4d646` | `d89189ffb06176ddcaee32328cca66d5013966638f7d38d8ec9441d6906fe984` | 2026-09-11 | AR-440-stale-hook-proof-20260911.json shows the older projection 79138e80adcc reporting drift against the real pointer, and the installed hook with scratch pointer and unknown config key blocking the Stop, naming 2e2fb18b6c25/afb7790bd7a2 plus stderr drift; strings match hooks.py:164-172. |
