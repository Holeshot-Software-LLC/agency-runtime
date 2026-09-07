---
title: "AR-174 documentation-only CI reconciliation evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, ci, documentation, cost, backlog]
related:
  - docs/decisions/0233-separate-hosted-run-timing-from-billing-administration.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - .github/workflows/ci.yml
  - scripts/classify_ci_change.py
  - scripts/check_ci_whitespace.py
  - tests/test_ci_change_scope.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
---

# AR-174: Documentation-only CI

## Scope and disposition

Read-only reconciliation after clean d43dc923 (PR #722's AR-173 merge plus
ledger), Linux/Python 3.12.3/Node 22.23.2, September 7. No production, test or
workflow change. Existing trusted-base scope and whitespace admission, merge-
revision code checks, head-only ledgers and five-runner docs topology remain
relevant. Current focused tests and source inspection confirm them.

The issue's claim that no hosted run had allocated runners was stale. A fresh
read of the historical August 31 PR #380 run supplies exact job timestamps
and a complete docs-only delta. This is one historical measurement, not current
billing health, matched before/after savings, a new Windows execution, or an
installed-harness proof. AR-156/159 and native producer obligations remain open.

Initially only criterion 8's universal final-release gate followed ADR-0105.
First verdicts remain at 5d20ec28: 2/3/4/6/8 satisfy; 1/5 need their own complete
workflow/matrix excerpts, and 7 measures raw duration but not billing repair.
ADR-0233 explicitly reconciles that account-administration clause with the
actual CI outcome: timestamp-bound eligible-run measurement, without a billing
claim. Original wording remains; criteria 1–6 stay unchanged. The final packet
adds existing workflow call sites/matrix and uses a new candidate for all eight
criteria. No production/test/script/workflow change or copied verdicts.

## Hosted run and pull request

Read September 7 via authenticated GitHub CLI; all commands are read-only.
The allocated successful run occurred after the July 27 issue's blocked-runner
report. It demonstrates the allocation block did not prevent this run; it
does not diagnose account billing changes or claim the current block is fixed.

```bash
gh pr view 380 --json number,url,baseRefOid,headRefOid,mergeCommit,mergedAt,files
gh api repos/Holeshot-Software-LLC/agency-runtime/actions/runs/33426445699 --jq '{id,html_url,head_sha,head_branch,created_at,run_started_at,updated_at,event,status,conclusion,run_attempt}'
git diff --raw --no-abbrev --no-renames 1a990beea0bc5af804a4285532a1e1c7c2c912c7...4c0aef6a24b78dfd80589f2d3b2ccdc3d17c45ba
git rev-parse 1a990beea0bc5af804a4285532a1e1c7c2c912c7:scripts/classify_ci_change.py HEAD:scripts/classify_ci_change.py 1a990beea0bc5af804a4285532a1e1c7c2c912c7:scripts/check_ci_whitespace.py HEAD:scripts/check_ci_whitespace.py
```

Exact output:

```text
{"baseRefOid":"1a990beea0bc5af804a4285532a1e1c7c2c912c7","files":[{"path":"docs/roadmap/README.md","additions":1,"deletions":1,"changeType":"MODIFIED"},{"path":"docs/roadmap/handoffs/issue-AR-338.md","additions":8,"deletions":5,"changeType":"MODIFIED"},{"path":"docs/roadmap/issue-AR-338-verify-windows-harness-set.md","additions":11,"deletions":4,"changeType":"MODIFIED"},{"path":"docs/worklog/README.md","additions":2,"deletions":0,"changeType":"MODIFIED"}],"headRefOid":"4c0aef6a24b78dfd80589f2d3b2ccdc3d17c45ba","mergeCommit":{"oid":"14782e302ecfde0c2d182e8618d8885d2c08a6b4"},"mergedAt":"2026-08-31T18:47:30Z","number":380,"url":"https://github.com/Holeshot-Software-LLC/agency-runtime/pull/380"}
{"conclusion":"success","created_at":"2026-08-31T18:41:52Z","event":"pull_request","head_branch":"claude/ar338-complete","head_sha":"4c0aef6a24b78dfd80589f2d3b2ccdc3d17c45ba","html_url":"https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/33426445699","id":33426445699,"run_attempt":1,"run_started_at":"2026-08-31T18:41:52Z","status":"completed","updated_at":"2026-08-31T18:46:45Z"}
:100644 100644 7a57478b4ee86b4691b5a4a27e86ff3a3d210a79 c34dd3a127a268fd237a2afbb51d320b2f614faf M	docs/roadmap/README.md
:100644 100644 c36b3e69efd991e066e1a665183cdda746a7326e f0705f821c75fdb18ae8275bc91911d9bbbc27f4 M	docs/roadmap/handoffs/issue-AR-338.md
:100644 100644 63f80893ca7f9f3f3415799b14d9a11133596d06 6809e081f9bbe242db693fc65a8d0200d7663e9e M	docs/roadmap/issue-AR-338-verify-windows-harness-set.md
:100644 100644 e12026d47cb2df9387c08196facf44e5e23c8f81 9feb2d476db7b9c4905c463360c69c0d4f954897 M	docs/worklog/README.md
a488d91cae5f2f84ce2eda0e0add552ec3278531
a488d91cae5f2f84ce2eda0e0add552ec3278531
8b38f1b5e0172656834f57e2db606b0cb8b9ae9b
8b38f1b5e0172656834f57e2db606b0cb8b9ae9b
```

Both helpers have identical Git blobs at the trusted historical base and
current HEAD: classifier a488d91cae5f2f84ce2eda0e0add552ec3278531 and whitespace
8b38f1b5e0172656834f57e2db606b0cb8b9ae9b. All four delta entries have 100644
old/new mode and docs Markdown paths. Current classifier applied to those
exact base/head SHAs returns (False, 'docs_markdown_only'); committed whitespace
returns b''. The successful historical quality job ran classification,
documentation dependencies, whitespace/hygiene and ledgers, and skipped Node,
development dependencies, fast/runtime tests and UI steps.

## Job times and calculation

```bash
gh api 'repos/Holeshot-Software-LLC/agency-runtime/actions/runs/33426445699/jobs?per_page=100' --jq '{total_count,jobs:[.jobs[]|{id,name,conclusion,started_at,completed_at,runner_name}]}'
```

Exact read-only output:

```json
{"jobs":[{"completed_at":"2026-08-31T18:42:21Z","conclusion":"success","id":99601073304,"name":"static quality, documentation, and dashboard UI","runner_name":"GitHub Actions 1000009056","started_at":"2026-08-31T18:41:54Z"},{"completed_at":"2026-08-31T18:43:49Z","conclusion":"success","id":99601217828,"name":"build and verify unsigned review distributions / ubuntu-24.04","runner_name":"GitHub Actions 1000009059","started_at":"2026-08-31T18:42:25Z"},{"completed_at":"2026-08-31T18:46:16Z","conclusion":"success","id":99601217840,"name":"build and verify unsigned review distributions / windows-2022","runner_name":"GitHub Actions 1000009060","started_at":"2026-08-31T18:42:23Z"},{"completed_at":"2026-08-31T18:42:21Z","conclusion":"skipped","id":99601219590,"name":"integration coverage / pair ${{ matrix.label }} of 2 / shards ${{ matrix.shard_a }}+${{ matrix.shard_b }}","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:42:21Z","conclusion":"skipped","id":99601219702,"name":"integration / full compatibility / ${{ matrix.label }} / py${{ matrix.python_a }}+py${{ matrix.python_b }}","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:42:21Z","conclusion":"skipped","id":99601219798,"name":"deterministic source checks and dependency audit","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:42:21Z","conclusion":"skipped","id":99601219801,"name":"portability contract / windows / py${{ matrix.python }}","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:42:22Z","conclusion":"skipped","id":99601220780,"name":"integration coverage / combined","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:42:21Z","conclusion":"skipped","id":99601222399,"name":"uninstrumented wall-clock performance","runner_name":null,"started_at":"2026-08-31T18:42:22Z"},{"completed_at":"2026-08-31T18:46:39Z","conclusion":"success","id":99602423292,"name":"assemble platform-honest unsigned review artifacts","runner_name":"GitHub Actions 1000009062","started_at":"2026-08-31T18:46:19Z"},{"completed_at":"2026-08-31T18:46:44Z","conclusion":"success","id":99602538091,"name":"automatic gates; integration suites are manual","runner_name":"GitHub Actions 1000009063","started_at":"2026-08-31T18:46:42Z"}],"total_count":11}
```

Subtract completed_at minus started_at only for jobs with an allocated runner.
Six skipped placeholder jobs have no runner (some timestamps are reversed by
GitHub); exclude them rather than inventing negative runner duration.

| Job ID | Allocated job | Raw seconds |
|---|---|---:|
| 99601073304 | static quality, documentation, and dashboard UI | 27 |
| 99601217828 | build and verify unsigned review distributions / ubuntu-24.04 | 84 |
| 99601217840 | build and verify unsigned review distributions / windows-2022 | 233 |
| 99602423292 | assemble platform-honest unsigned review artifacts | 20 |
| 99602538091 | automatic gates; integration suites are manual | 2 |
| Total | Five allocated successful jobs | 366 |

27 + 84 + 233 + 20 + 2 = 366 seconds = 6.10 raw runner-minutes.
Run creation-to-update span is 293 seconds (4 minutes 53 seconds); parallel
jobs make this different from summed runner time. Neither number includes
billing rounding, platform multipliers, or a matched baseline. No percentage
speed or cost saving is inferred. Job-count history (13 then 10 code runners)
is distinct from the five-runner docs lane.

## Focused workflow transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_ci_change_scope.py tests/test_ci_sharding.py tests/test_ci_session_pair.py tests/test_release_packaging.py tests/test_run_local_gates.py -k 'not windows' -q -W error
```

Complete stdout, exit zero (second unchanged-source run; first passed 235
with five deselections in 6.59s):

```text
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 91%]
...................                                                      [100%]
235 passed, 5 deselected in 6.45s
```

The five Windows-named cases are excluded under the owner's native-Windows
boundary, not claimed passing. No failure, xfail or skip was introduced.
All scope, sharding and pair/session tests plus non-Windows release/workflow
and required-local-gate contracts run in this command.

## Shell and security transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -c 'import pathlib, subprocess, yaml; count=0
for path in sorted(pathlib.Path(".github/workflows").glob("*.yml")):
 for job in yaml.safe_load(path.read_text())["jobs"].values():
  for step in job.get("steps", []):
   if "run" in step and step.get("shell") == "bash":
    result=subprocess.run(["bash", "-n"], input=step["run"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, (str(path), step.get("name"), result.stderr)
    count += 1
print(f"Bash syntax passed for {count} explicit bash workflow steps")' && env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_release_hygiene.py
```

Actual output, exit zero:

```text
Bash syntax passed for 18 explicit bash workflow steps
Release hygiene check passed (2360 release input files).
```

This checks every explicitly Bash workflow step with bash -n, not a claim
that shellcheck or actionlint ran. The pinned offline workflow scanner was
invoked through an isolated uvx tool environment:

```bash
uvx --from zizmor==1.26.1 zizmor --pedantic --strict-collection --offline .
```

Actual output, exit zero:

```text
Installed 1 package in 6ms
 INFO zizmor: 🌈 zizmor v1.26.1
 INFO audit: zizmor: 🌈 completed ./.github/dependabot.yml
 INFO audit: zizmor: 🌈 completed ./.github/workflows/ci.yml
 INFO audit: zizmor: 🌈 completed ./.github/workflows/codeql.yml
 INFO audit: zizmor: 🌈 completed ./.github/workflows/dependency-review.yml
 INFO audit: zizmor: 🌈 completed ./.github/workflows/roster-upstream-audit.yml
No findings to report. Good job! (1 suppressed)
```

The one existing suppression is unchanged. No new suppression or relaxed gate.

## Production spine transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_storage_file_trust.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_upstream_selection_eval.py tests/test_decision_conformance.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_owner_authority.py tests/test_security_turn_boundaries.py tests/test_canary_coverage_complete.py tests/test_complexity_refactors.py tests/test_coverage_final_host_cli.py tests/test_resident_manager_lifecycle.py -q -W error
```

Final stdout chunk, exit zero (earlier progress lines omitted):

```text
.....................................................ss.. [ 66%]
........................................................................ [ 72%]
........................................................................ [ 79%]
........................................................................ [ 86%]
........................................................................ [ 92%]
........................................................................ [ 99%]
........                                                                 [100%]
1085 passed, 3 skipped in 69.45s (0:01:09)
```

The three skips are existing platform-dependent cases; no test or product
source changes in this package.

## UI and current coverage transcript

```bash
set -o pipefail
node --test --experimental-test-coverage '--test-coverage-include=agency_runtime/dashboard/**/*.js' --test-coverage-lines=95 --test-coverage-branches=86 --test-coverage-functions=93 tests/dashboard_ui.test.mjs | tail -28
```

Actual final 28 output lines, exit zero, with display-only trailing padding
removed for repository whitespace policy:

```text
  type: 'test'
  ...
1..200
# tests 204
# suites 0
# pass 204
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 248.962295
# start of coverage report
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# file                   | line % | branch % | funcs % | uncovered lines
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# agency_runtime         |        |          |         |
#  dashboard             |        |          |         |
#   app.js               |  95.45 |    87.96 |   71.70 | 431 467-469 483-490 515-520 524-525 530-536
#   charts.js            | 100.00 |   100.00 |  100.00 |
#   dashboard-actions.js |  94.53 |    47.10 |  100.00 | 128-129 132-133 149 159-160 176-177 211-214 243 252-253 276 311 319-320 348 389-390 393-394 429 473
#   dashboard-config.js  |  99.28 |    96.69 |  100.00 | 230-231 291-292
#   dashboard-core.js    |  99.05 |    92.98 |  100.00 | 345-346 449 482-483
#   dashboard-live.js    |  95.34 |    87.39 |   98.77 | 63-64 242-244 276-277 360-363 372-373 676 750-751 798-831 852-854 863 875 903-904 938 1229-1230 1237-1238 1354-1355 1362 1441-1442 1627-1628 1767-1769 1784-1787 1796-1799 1893 1924-1925 1938-1940 1964-1966 1969-1970 2045-2046 2048-2049 2060-2061 2215 2248 2356-2364 2378-2382 2390-2391 2400-2401 2431-2432
#   dashboard-render.js  |  97.96 |    86.25 |   97.01 | 120-128 777-782 896-897 933-935 1458 1461-1462 1494-1495 1654-1655 1923-1928 2323-2340
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# all files              |  96.93 |    86.78 |   95.73 |
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# end of coverage report
```

Runtime/test/script/workflow Git diff against accepted AR-173 candidate
594bc4d3939d144440ae52f5acdf5f840c79f25e exits zero. AR-165's earlier curated
184/184 mutation and AR-172's 39 routing checks remain earlier evidence only;
no rerun or live staffing claim. Exhaustive corpus/shards/matrix not dispatched.

## Record checks

The first draft's criterion-5 source requested line 850, beyond the workflow's
847-line EOF. Strict documentation validation rejected that invalid range;
the citation was corrected before any verifier invocation. No product failure
or acceptance verdict was suppressed. Staged release hygiene also passes:

```text
Release hygiene check passed (2362 release input files).
```

The command sequence below uses set -e so the first failure stops the gate.


```bash
set -e
export PYTHONPATH=.
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_policy_availability.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_worklog.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py --require-tracker
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_tracker.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime tests scripts
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime tests scripts
git diff --check
```

Actual stdout, exit zero:

```text
checked 1209 Markdown documents
worklog index is current (2023 commits)
documentation validation passed for 1209 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```


Final requirement/call-site reconciliation checks, exit zero. Product, tests,
scripts and workflow bytes compare unchanged against first candidate 452639dd.

```bash
set -e
export PYTHONPATH=.
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_policy_availability.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_worklog.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py --require-tracker
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_tracker.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime tests scripts
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime tests scripts
git diff --check
git diff --exit-code 452639dda089ea3304e04824beaf9b79e8c1febe -- agency_runtime tests scripts .github
```

```text
checked 1211 Markdown documents
worklog index is current (2026 commits)
documentation validation passed for 1211 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```
