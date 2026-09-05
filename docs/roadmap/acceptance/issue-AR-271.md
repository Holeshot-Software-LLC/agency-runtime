---
title: "AR-271 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, uninstall, openclaw]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-271
candidate_commit: 4fdcd6a7b1ff3ae3ab8a666937adeb5d1111895b
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-271 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `Installation runs its original native probe then invokes the extracted bounded classifier with unchanged stopped/live semantics` | 2026-09-05 | `agency_runtime/core/installer_registration.py:123-183` |
| 1 | file | `Uninstall imports that same classifier` | 2026-09-05 | `agency_runtime/core/installer_uninstall.py:11-29` |
| 1 | file | `Production uninstall obtains a bound probe and applies the shared classification before granting stopped state` | 2026-09-05 | `agency_runtime/core/installer_uninstall.py:809-863` |
| 1 | test | `Install/uninstall parity for exact exit-1 stopped, legacy stopped/live, truncated and other nonzero responses` | 2026-09-05 | `tests/test_host_uninstall.py:964-983` |
| 2 | test | `Eleven negative shapes leave plans blocked, execute no native mutation and preserve the whole disposable home` | 2026-09-05 | `tests/test_host_uninstall.py:864-909` |
| 2 | file | `Complete JSON, truncation checks and explicit live precedence govern the shared classifier` | 2026-09-05 | `agency_runtime/core/installer_registration.py:139-183` |
| 2 | command-output | `Regression-first failures and focused passing command are retained with explicit injected-contract scope` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md:19-60` |
| 3 | test | `Write-free plan then reversible owned retirement for present and absent native plugin; repeated probes, unchanged retained bytes and no gateway lifecycle commands` | 2026-09-05 | `tests/test_host_uninstall.py:801-861` |
| 3 | test | `Live and unknown state after approval and immediately before commit block plugin mutation and preserve owned bytes` | 2026-09-05 | `tests/test_host_uninstall.py:912-961` |
| 3 | test | `Owner-verification denial blocks OpenClaw and Codex mutation` | 2026-09-05 | `tests/test_host_uninstall.py:475-511` |
| 3 | test | `Changed launcher/environment/final revalidation refuses the production bound-probe launch path before execution` | 2026-09-05 | `tests/test_host_uninstall.py:986-1033` |
| 3 | file | `Native bound runner verifies launcher, environment, forbidden roots, cwd and revalidation before bounded execution` | 2026-09-05 | `agency_runtime/core/installer_uninstall.py:615-689` |
| 3 | file | `Prepared transaction checks owner authority, locked plan and aggregate binding before invoking the private commit` | 2026-09-05 | `agency_runtime/core/prepared_host_uninstall.py:378-468` |
| 3 | file | `Private commit repeats native preflight and binding comparison before uninstall mutation` | 2026-09-05 | `agency_runtime/core/installer_uninstall.py:1352-1416` |
| 3 | command-output | `Passing disposable-home tests explicitly do not claim a real gateway restart or live uninstall` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md:41-75` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
