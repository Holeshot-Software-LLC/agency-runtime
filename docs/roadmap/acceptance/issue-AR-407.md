---
title: "AR-407 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, install, drift]
related:
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
  - docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-407
candidate_commit: dcd587209aced5e4d7e74f80c2e4df2df00a1e50
evidence_cutoff: 2026-09-07
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/727
---

# AR-407 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `Generic install passes resolved targets through residual text and JSON; helper filters reports by host` | 2026-09-07 | `agency_runtime/cli/install_commands.py:1796-1903` |
| 1 | test | `Real-pointer matrix checks explicit/default/all/empty targets in text and JSON, including unrelated-first and selected foreign drift` | 2026-09-07 | `tests/test_cli_install_drift.py:47-149` |
| 1 | command-output | `Expanded focused package passes 158 with one Windows-named deselection; independent review reruns 35` | 2026-09-07 | `docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md:178-194` |
| 2 | file | `Resolved install targets reflect explicit selection or detected installed hosts` | 2026-09-07 | `agency_runtime/cli/install_commands.py:284-292` |
| 2 | test | `Multi-target/default/all matrix preserves selected host drift and rejects unrelated reports` | 2026-09-07 | `tests/test_cli_install_drift.py:47-140` |
| 2 | file | `Global status still publishes every report in runtime_drift_hosts` | 2026-09-07 | `agency_runtime/cli/install_commands.py:2485-2509` |
| 2 | test | `Global status retains OpenClaw foreign-package drift with Codex current` | 2026-09-07 | `tests/test_cli_install_drift.py:161-194` |
| 3 | command-output | `Focused regression result and independent review` | 2026-09-07 | `docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md:178-194` |
| 3 | command-output | `Exact candidate helper fragments against actual live mixed pointers, with hashes, target results and unchanged file/directory metadata` | 2026-09-07 | `docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md:196-286` |
| 3 | command-output | `Portable artifact under restrictive producer umask, independent verification, exact installed source hash and isolated packaged MCP/dashboard smoke` | 2026-09-07 | `docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md:17-82` |
| 3 | command-output | `Fresh installed aggregate all-host smoke passes eight checks; native turns and owner integration changes explicitly excluded` | 2026-09-07 | `docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md:83-157` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-407.1-20260907-713053f0` | `60006339af01d150a902d2453b2c07852b77cc1c50721d9cc3bf6ea753f0e726` | 2026-09-07 | install_commands.py:1804-1876 filters residual drift to resolved targets and uses that same value for both the text warning (1818-1824) and JSON runtime_drift (1850); tests/test_cli_install_drift.py:52-149 covers --agent codex with stale unrelated host suppressed and requested-host drift retained. |
| 2 | satisfied | `AR-407.2-20260907-04674097` | `25e4393f7dd6ba012f34bc8e39a0f34c17537653f1f3afd8b57103248e61b81c` | 2026-09-07 | install_commands.py:1804 scopes residual drift to targets resolved at :1696/:284 (--all and default expand to detected hosts), while cmd_status :2494-2502 publishes unfiltered drift projections in runtime_drift_hosts; tests/test_cli_install_drift.py:52-139 and 161-194 cover both paths. |
| 3 | satisfied | `AR-407.3-20260907-97b36013` | `c28e7907292755ac05e2e486957711857a30d215bdb6892d0aee0acefac6b1f4` | 2026-09-07 | Evidence lines 178-194 show 158 focused drift tests passing; lines 196-286 show an exact candidate-helper probe (source sha 659b42b2, matching installed) on five live pointers, unchanged pointers/dirs, no permission repairs or credential/trust changes; snapshot confirms target-scoped projection. |
