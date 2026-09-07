---
title: "AR-177 manual-only CI reconciliation evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, ci, testing, cost, backlog]
related:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0234-retire-superseded-manual-ci-checklist.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md
supersedes: []
superseded_by: null
---

# AR-177 manual-only CI reconciliation evidence

## Disposition boundary

Retire the superseded mandatory manual-run/release checklist, not the working
manual-only implementation and not as a satisfied acceptance result. Original
implementation 60543e164aab2dd2e9907e81b3b06f201f50d190 is dated July 27:
`ci: run exhaustive Python verification on demand`.
Current inspected main is d2125438910d873a116a11b2ce2cb7f27209beeb.
No workflow, runtime, test, artifact profile, coverage floor or billing changes.

## Current source contracts

- .github/workflows/ci.yml:301-355: coverage has an explicit manual-event
  condition before its two paired jobs, covering shards 0/1 and 2/3.
- .github/workflows/ci.yml:357-384: dependent combination retains fail-under=97.
- .github/workflows/ci.yml:429-485: compatibility retains explicit manual
  admission and Linux 3.10/3.11, Linux 3.12/3.14, Windows 3.10/3.14 pairs.
- .github/workflows/ci.yml:770-847: the aggregate distinguishes automatic skip
  from required manual success and rejects missing/incoherent gate results.
- tests/test_release_packaging.py:710-745 and 985-1117 execute those event and
  result contracts; tests/test_ci_session_pair.py retains the exact session
  members, process isolation, cancellation, timeout and evidence controls.

These are current structural/behavioral workflow tests, not measured hosted
runner savings, a completed manual integration run or a Windows-native run.

## Fresh focused execution

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_ci_change_scope.py tests/test_ci_session_pair.py tests/test_release_packaging.py -q -W error -k 'not windows'
```

```text
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 97%]
......                                                                   [100%]
222 passed, 5 deselected in 6.70s
```

Five Windows-named cases are deselected; no tests are skipped or disabled by
this change. AR-176's just-merged named spine (1085/three existing skips),
UI 224/current floors and native observations remain separately dated.
A source equality check passes:
```bash
git diff --exit-code d2125438910d873a116a11b2ce2cb7f27209beeb -- agency_runtime tests scripts .github pyproject.toml
```
It emits no differences. No fresh spine, UI, artifact or native-harness run is
invented for this documentation-only disposition.

## Read-only hosted history

The current API enumeration returned one retained manual CI run, not thirty
successful samples. No new workflow was dispatched and no settings changed.

```bash
gh run list --workflow ci.yml --event workflow_dispatch --limit 30 --json databaseId,headSha,event,status,conclusion,createdAt,updatedAt,name,url,headBranch
```

```json
[
  {
    "conclusion": "failure",
    "createdAt": "2026-08-17T02:38:31Z",
    "databaseId": 31988612867,
    "event": "workflow_dispatch",
    "headBranch": "claude/remote-control-14de96",
    "headSha": "8f00ac95a18b929db1d251684dfb233259f8555a",
    "name": "CI",
    "status": "completed",
    "updatedAt": "2026-08-17T02:39:03Z",
    "url": "https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/31988612867"
  }
]
```

[Run 31988612867](https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/31988612867)
at 8f00ac95 failed in its quality job's patch-whitespace step. The aggregate
then failed. Coverage and compatibility had no allocated runners. This does
not satisfy the old request for a complete manual topology run; it also does
not establish a billing block or a repaired billing account.

```bash
gh api repos/Holeshot-Software-LLC/agency-runtime/actions/runs/31988612867/jobs
```

The following projection preserves all ten returned job outcomes, timestamps,
runner allocation labels and step outcomes; unrelated API metadata is omitted:
```json
{
  "jobs": [
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "failure",
      "id": 95267938296,
      "name": "static quality, documentation, and dashboard UI",
      "runner_name": "GitHub Actions 1000008006",
      "started_at": "2026-08-17T02:38:36Z",
      "status": "completed",
      "steps": [
        {
          "conclusion": "success",
          "name": "Set up job"
        },
        {
          "conclusion": "success",
          "name": "Check out source"
        },
        {
          "conclusion": "success",
          "name": "Set up Python"
        },
        {
          "conclusion": "success",
          "name": "Classify the complete event delta"
        },
        {
          "conclusion": "success",
          "name": "Set up Node.js"
        },
        {
          "conclusion": "success",
          "name": "Install development dependencies"
        },
        {
          "conclusion": "success",
          "name": "Prepare private quality runtime"
        },
        {
          "conclusion": "skipped",
          "name": "Install documentation dependencies"
        },
        {
          "conclusion": "success",
          "name": "Check dependency consistency"
        },
        {
          "conclusion": "success",
          "name": "Check Python code quality"
        },
        {
          "conclusion": "failure",
          "name": "Check patch whitespace"
        },
        {
          "conclusion": "skipped",
          "name": "Check tracked release inputs"
        },
        {
          "conclusion": "skipped",
          "name": "Verify fast workflow contracts"
        },
        {
          "conclusion": "skipped",
          "name": "Run fast Python production spine"
        },
        {
          "conclusion": "skipped",
          "name": "Run AR-119 matrix evidence"
        },
        {
          "conclusion": "skipped",
          "name": "Prove decision-conformance mutations"
        },
        {
          "conclusion": "skipped",
          "name": "Run dashboard UI tests with coverage"
        },
        {
          "conclusion": "skipped",
          "name": "Check out canonical documentation history"
        },
        {
          "conclusion": "skipped",
          "name": "Verify documentation ledgers"
        },
        {
          "conclusion": "skipped",
          "name": "Post Set up Node.js"
        },
        {
          "conclusion": "skipped",
          "name": "Post Set up Python"
        },
        {
          "conclusion": "success",
          "name": "Post Check out source"
        },
        {
          "conclusion": "success",
          "name": "Complete job"
        }
      ]
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993139,
      "name": "portability contract / windows / py${{ matrix.python }}",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:57Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993183,
      "name": "deterministic source checks and dependency audit",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:57Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:39:02Z",
      "conclusion": "failure",
      "id": 95267993251,
      "name": "automatic gates; integration suites are manual",
      "runner_name": "GitHub Actions 1000008008",
      "started_at": "2026-08-17T02:38:59Z",
      "status": "completed",
      "steps": [
        {
          "conclusion": "success",
          "name": "Set up job"
        },
        {
          "conclusion": "failure",
          "name": "Require every applicable production gate"
        },
        {
          "conclusion": "success",
          "name": "Complete job"
        }
      ]
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993322,
      "name": "integration / full compatibility / ${{ matrix.label }} / py${{ matrix.python_a }}+py${{ matrix.python_b }}",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993324,
      "name": "integration coverage / pair ${{ matrix.label }} of 2 / shards ${{ matrix.shard_a }}+${{ matrix.shard_b }}",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993382,
      "name": "build and verify unsigned review distributions / ${{ matrix.os }}",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993416,
      "name": "uninstrumented wall-clock performance",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993557,
      "name": "integration coverage / combined",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    },
    {
      "completed_at": "2026-08-17T02:38:57Z",
      "conclusion": "skipped",
      "id": 95267993644,
      "name": "assemble platform-honest unsigned review artifacts",
      "runner_name": null,
      "started_at": "2026-08-17T02:38:58Z",
      "status": "completed",
      "steps": []
    }
  ],
  "total_count": 10
}
```

## Remaining scope

Existing ADR-0105/AR-186 make exhaustive diagnostics optional and explicitly
requested, not ordinary issue or release vetoes. AR-156/159 retain their own
platform/enforcement obligations. AR-176 retains its two unaccepted inventory
criteria. This retirement does not close those records or certify coverage.
