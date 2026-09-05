---
title: "AR-348 resolved hiring independence evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, hiring, regression, configuration]
related:
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/decisions/0221-enforce-hiring-independence-on-resolved-provider-chains.md
  - tests/test_workforce_dynamic_hiring.py
  - agency_runtime/core/inference_profiles.py
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/evals/decision_conformance.py
supersedes: []
superseded_by: null
type: evidence
---

# AR-348 resolved hiring independence evidence

## Scope

One outcome: strict=true rejects overlapping effective creator/reviewer chains;
strict=false keeps warning-only hiring. Original AR-348 acceptance is unchanged.
The old ticket's proposed global-profile-only implementation was insufficient.
Tests invoke hire_contractor_for_gap with real parsing, compilation, review
flow and Store persistence, deterministic fake provider replies, and temporary
databases. These are offline production-path checks, not paid-provider quality
evaluation, installed host activation, or native Windows evidence.

## Regression-first reproduction

Source baseline: 6307e17dec4468d84cc192b2d85ea00b8d039b0d. Red tests and
canonical scope are committed in 2e5454bc33fd9f908782e95bd5f33257e4e1b7b1.

```text
python -m pytest tests/test_workforce_dynamic_hiring.py \
  -k strict_independence -q -W error --tb=short
20 failed, 23 passed, 70 deselected in 14.14s
```

All 20 negatives fail because ConfigValidationError is not raised. Both
critic/security routes are covered across nine sources: explicit profile,
default profile, harness route, environment-selected harness, legacy reviewer,
entirely legacy chains, creator fallback, reviewer fallback, shared fallback.
Two additional negatives cover safety-repair primary and fallback overlap.
All non-strict controls and three distinct-provider normal/repair flows pass.

The first implementation run yielded one failure/42 passes: the entirely
legacy error named only the first conflicting route. Preflight now aggregates
both conflicts in the same existing helper. No assertion was weakened.

## Focused verification

Final targeted package, after two additional invocation-boundary recheck tests:

```text
python -m pytest tests/test_workforce_dynamic_hiring.py \
  tests/test_inference_profiles.py tests/test_workforce_hiring_contract.py \
  tests/test_workforce_inference.py tests/test_workforce_selection_safety.py \
  -q -W error --tb=short
413 passed, 1 skipped in 20.52s
```

The strict initial tests require the named config error, zero calls, no hiring
case and no enabled worker. Safety-repair overlap requires exactly the preceding
three initial calls, no replacement call, no applied case and no worker.
Non-strict tests require successful registration and the exact stored warning,
not just absence of an exception. Distinct-profile controls still hire normally
and through both critic repair and safety repair. Two more tests change a
reviewer route after preflight and require the invocation guard to reject it.

## Fast verification

- Named AGENTS.md 29-file spine: 1075 passed, three existing skips, 72.29s.
- Configured UI coverage command: 138 passed, zero skipped; all seven production
  modules, 96.92 percent lines / 86.62 branches / 95.71 functions. Floors remain
  95/86/93. No UI source, behavioral tests or measurement scope changed here.
- Ruff check passes; all 764 Python files pass formatting.
- Routing evaluation: passed, all gates true; deterministic candidate recall
  only. This is not a measured improvement to live staffing's 75-second latency.
- The first attempted CLI invocation used python -m agency_runtime, but this
  package has no __main__; it failed before evaluating anything. The repository's
  actual agency_runtime.cli.entrypoint.main entry point then passed routing.
- Two curated mutation cases now target strict enforcement and zero-call
  preflight. Their catalog/runner tests pass: 17 passed in 0.25s. The prior
  full spine preceded only this catalog addition; runtime source is unchanged.

## Verification at implementation checkpoint

The new 184-case protected conformance run, isolated acceptance verdicts,
merged-main delivery and installed smoke remain pending at this checkpoint.
No old 182-case result is claimed as this package's evidence. No exhaustive
Python/coverage matrix, live host canary, new credential or hook-trust change.

## Post-candidate verification

Both original criteria received satisfied isolated Codex verdicts against
c9b678a5: AR-348.1-20260905-7e0a8723 and AR-348.2-20260905-161d16c3.
No acceptance criterion was changed and no second judgment pass was needed.

The first 184-case conformance attempt failed baseline fixture setup in 1.059s,
before any mutation or test failure node: ensure_private_directory rejected the
copied offline-config creation boundary. Source remained unchanged. A bounded
two-mutation diagnostic reproduced the same fixture error (1.117s), again with
zero mutations run and source unchanged. Shell umask is 0002; AR-297 and the
prior AR-405 receipt already document protected 0077 execution for this gate.
The successful rerun sets umask only in the evaluation process. No existing filesystem
permissions, validation check, test, or product behavior is altered by that fix.

The complete protected rerun passes its baseline in 98.879s and kills all 184
mutations: zero survived, zero invalid, source_unchanged=true. The new
strict-hiring-independence-disabled mutation is killed in 1.448s and
strict-hiring-preflight-skipped in 1.190s, both by the exact
profile-security_review-True regression node. No runtime source changed after
the c9b678a5 acceptance candidate. Command (with a test-equipped interpreter):

```bash
python -c 'import os; os.umask(0o077); from agency_runtime.cli.entrypoint import main; raise SystemExit(main())' \
  eval decision-conformance --repository . --json
```

PR #687 main publication and merged installed delivery remain pending at this
verification checkpoint. The failed receipts above remain part of the record.
