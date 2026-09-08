---
title: "AR-190 second-review acceptance evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-08
tags: [acceptance, verification, updates, uv, release]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-190
candidate_commit: pending
evidence_cutoff: 2026-09-08
tracker_url: null
---

# AR-190 second-review acceptance evidence

First-review verdicts remain faithfully committed at a6efa01b, ledger
0199f8d3: four satisfied, criterion 5 absent. This new builder is pending,
with new d1a9260c exact-source installed proof and the explicit product-source
criterion clarification. A new receipt candidate changes every digest, so
no prior verdict is reused. The second and final review must run all five.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Installer chooses interpreter-bound isolated pip only without a uv receipt and after capability validation | 2026-09-07 | agency_runtime/core/update_service.py:1032-1070 |
| 1 | test | Exact-SHA plan and isolated pip command expectations | 2026-09-07 | tests/test_update_service.py:457-502 |
| 1 | test | Pip-only selection preserves the bound interpreter and isolated configuration flags | 2026-09-07 | tests/test_update_service.py:780-812 |
| 1 | command-output | Fresh focused update and CLI test command and stdout | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#fresh-focused-checks |
| 2 | file | Exact bounded uv receipt and private in-prefix entrypoint validation | 2026-09-07 | agency_runtime/core/update_service.py:1071-1123 |
| 2 | file | Safe uv resolution before generating installer argv | 2026-09-07 | agency_runtime/core/update_service.py:1125-1190 |
| 2 | file | No-config default-directory binding before generating installer argv | 2026-09-07 | agency_runtime/core/update_service.py:1191-1263 |
| 2 | test | Validated uv ownership is selected ahead of pip and emits uv-tool argv | 2026-09-07 | tests/test_update_service.py:595-643 |
| 2 | command-output | Real uv-generated receipt and no-pip installed environment | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#legitimate-uv-installation |
| 2 | command-output | Actual installed CLI emits exact-SHA uv command and returns installer uv-tool | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#same-candidate-installed-plan |
| 3 | test | Unsafe uv resolution fails closed | 2026-09-07 | tests/test_update_service.py:513-593 |
| 3 | test | Target overrides, wrong directories and renamed tool environments are rejected | 2026-09-07 | tests/test_update_service.py:674-756 |
| 3 | test | No-pip environment without validated uv returns unavailable | 2026-09-07 | tests/test_update_service.py:758-778 |
| 3 | test | Receipt shape, wrong entrypoint, ambiguity and missing receipt are rejected | 2026-09-07 | tests/test_update_service.py:814-880 |
| 3 | test | Oversized receipt and unsafe symlinks are rejected | 2026-09-07 | tests/test_update_service.py:881-948 |
| 3 | command-output | Fresh focused tests covering unavailable environments | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#fresh-focused-checks |
| 4 | file | Planner only constructs immutable package and isolated host-refresh commands | 2026-09-07 | agency_runtime/core/update_service.py:1285-1356 |
| 4 | file | CLI renders the plan and exits without dispatching generated commands | 2026-09-07 | agency_runtime/cli/upgrade_commands.py:93-118 |
| 4 | file | Upgrade dashboard action copies the fixed command rather than executing it | 2026-09-07 | agency_runtime/dashboard/app.js:409-420 |
| 4 | test | CLI JSON retains mutation_performed false | 2026-09-07 | tests/test_cli_upgrade.py:105-133 |
| 4 | command-output | Real plan interval preserves 669 compared prefix files, uv receipt and entrypoint; no printed command executed | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#no-plan-mutations-and-isolation-bounds |
| 5 | command-output | Fresh clean detached d1a9260c canonical artifacts, strict Twine and independent portable verifier | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#canonical-exact-source-build |
| 5 | command-output | Actual installed uv-tool plan from and to exact d1a9260c product-source candidate | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#same-candidate-installed-plan |
| 5 | command-output | Fresh 67 focused tests and targeted Ruff lint/format on detached d1a9260c | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#fresh-focused-checks |
| 5 | command-output | Passing metadata, documentation, worklog, policy and diff gates at the corresponding evidence checkpoint | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#record-checkpoint-gates |
| 5 | command-output | Exact source checksums, installed planner checksums and empty runtime/test/build-source Git diff | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#concrete-source-identity |
| 5 | file | Owner-requested product-source versus later receipt-commit distinction preserves the original criterion and all runtime guards | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md#product-source-and-receipt-distinction |

## Verification

No verdicts while pending. The first review remains in commit a6efa01b.
The isolated runner owns every verdict in the second and final all-five run.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
