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
