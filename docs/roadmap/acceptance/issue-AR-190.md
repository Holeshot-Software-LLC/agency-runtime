---
title: "AR-190 pending acceptance evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, updates, uv, release]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-190
candidate_commit: pending
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-190 pending acceptance evidence

Builder evidence only. Parent must integrate the shared ledger, preserve the
actual documentation gate result, commit the evidence and freeze this record
before invoking isolated verification. The live installed artifact and plan
are both bound to c64ce3ce54c6e51280292298b5e3600611cb72fc; a later record-only
candidate must retain that source-equivalence explanation. No verdict is
claimed from the original checked boxes.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Installer chooses interpreter-bound isolated pip only without a uv receipt and after capability validation | 2026-09-07 | agency_runtime/core/update_service.py:1032-1070 |
| 1 | test | Exact-SHA plan and isolated pip command expectations | 2026-09-07 | tests/test_update_service.py:457-502 |
| 1 | test | Pip-only selection preserves the bound interpreter and isolated configuration flags | 2026-09-07 | tests/test_update_service.py:780-812 |
| 1 | command-output | Fresh focused update and CLI test command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#focused-checks |
| 2 | file | Exact bounded uv receipt and private in-prefix entrypoint validation | 2026-09-07 | agency_runtime/core/update_service.py:1071-1123 |
| 2 | file | Safe uv resolution before generating installer argv | 2026-09-07 | agency_runtime/core/update_service.py:1125-1190 |
| 2 | file | No-config default-directory binding before generating installer argv | 2026-09-07 | agency_runtime/core/update_service.py:1191-1263 |
| 2 | test | Validated uv ownership is selected ahead of pip and emits uv-tool argv | 2026-09-07 | tests/test_update_service.py:595-643 |
| 2 | command-output | Real uv-generated receipt and no-pip installed environment | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#legitimate-uv-installation |
| 2 | command-output | Actual installed CLI emits exact-SHA uv command and returns installer uv-tool | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#final-installed-plan |
| 3 | test | Unsafe uv resolution fails closed | 2026-09-07 | tests/test_update_service.py:513-593 |
| 3 | test | Target overrides, wrong directories and renamed tool environments are rejected | 2026-09-07 | tests/test_update_service.py:674-756 |
| 3 | test | No-pip environment without validated uv returns unavailable | 2026-09-07 | tests/test_update_service.py:758-778 |
| 3 | test | Receipt shape, wrong entrypoint, ambiguity and missing receipt are rejected | 2026-09-07 | tests/test_update_service.py:814-880 |
| 3 | test | Oversized receipt and unsafe symlinks are rejected | 2026-09-07 | tests/test_update_service.py:881-948 |
| 3 | command-output | Fresh focused tests covering unavailable environments | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#focused-checks |
| 4 | file | Planner only constructs immutable package and isolated host-refresh commands | 2026-09-07 | agency_runtime/core/update_service.py:1285-1356 |
| 4 | file | CLI renders the plan and exits without dispatching generated commands | 2026-09-07 | agency_runtime/cli/upgrade_commands.py:93-118 |
| 4 | file | Upgrade dashboard action copies the fixed command rather than executing it | 2026-09-07 | agency_runtime/dashboard/app.js:409-420 |
| 4 | test | CLI JSON retains mutation_performed false | 2026-09-07 | tests/test_cli_upgrade.py:105-133 |
| 4 | command-output | Real plan interval preserves 669 compared prefix files, uv receipt and entrypoint; no printed command executed | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#no-execution-and-before-after-evidence |
| 5 | command-output | Clean detached exact-c64 canonical wheel, strict Twine and independent portable verifier | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#canonical-artifact-identity |
| 5 | command-output | Actual installed uv-tool plan from and to the same exact c64 source commit | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#final-installed-plan |
| 5 | command-output | Fresh 67-test update/CLI result and targeted Ruff lint/format output | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#focused-checks |
| 5 | command-output | Passing documentation and diff gates after normal merge-ledger reconciliation, with earlier failure preserved | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#record-checks |
| 5 | command-output | Exact live-source commit and record-only candidate have unchanged runtime, producer, tests and packaging configuration | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md#record-candidate-source-equivalence |

## Verification

No verdict rows: candidate is pending. Do not mark the issue done from builder
evidence or substitute the earlier 08fab1c4-to-c64ce3ce run for the final
same-commit installed-candidate proof.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
