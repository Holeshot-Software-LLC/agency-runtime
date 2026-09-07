---
title: "AR-164 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, executables, security]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-164
candidate_commit: 083ae8b58378d97c139cfb79debf0a49175b3f92
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-164 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Inert marker lstat walk returns every repository ancestor without invoking Git | 2026-09-07 | agency_runtime/core/process_argv.py:299-333 |
| 1 | test | Nested working directory excludes poisoned sibling bin and resolves external tool | 2026-09-07 | tests/test_executable_discovery_security.py:77-110 |
| 1 | command-output | Fresh 38-case executable boundary suite passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 2 | file | First Git preparation derives roots and resolves Git only outside those boundaries | 2026-09-07 | agency_runtime/core/git_runner.py:142-201 |
| 2 | test | Root-discovery call captures prepared real Git and rejects sibling repository Git | 2026-09-07 | tests/test_executable_discovery_security.py:323-351 |
| 2 | command-output | Fresh boundary and surviving Git suites execute successfully | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 3 | file | Explicit and resolver results share final forbidden-root validation | 2026-09-07 | agency_runtime/core/process_argv.py:387-455 |
| 3 | test | Explicit repository argv and one-argument resolver cannot bypass the boundary | 2026-09-07 | tests/test_executable_discovery_security.py:136-154 |
| 3 | file | Freezing independently checks every resolved artifact against the roots | 2026-09-07 | agency_runtime/core/process_argv.py:757-832 |
| 3 | command-output | Resolver and explicit-path cases pass in the complete executable suite | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 4 | file | Native Windows path spelling and case normalization use ntpath semantics | 2026-09-07 | agency_runtime/core/process_argv.py:232-297 |
| 4 | test | Cross-drive and mixed-case CMD paths cannot cross the root | 2026-09-07 | tests/test_executable_discovery_security.py:66-74 |
| 4 | test | Case-insensitive Windows wrapper is refused | 2026-09-07 | tests/test_executable_discovery_security.py:156-163 |
| 4 | test | Untrusted PATHEXT COM candidates and fallback resolutions are rejected | 2026-09-07 | tests/test_executable_discovery_security.py:473-520 |
| 4 | test | Real link alias into repository is rejected | 2026-09-07 | tests/test_executable_discovery_security.py:188-204 |
| 4 | file | Final root check compares both lexical spelling and resolved target | 2026-09-07 | agency_runtime/core/process_argv.py:733-775 |
| 4 | command-output | Portable spelling/PATHEXT simulations and actual Linux link cases pass; native Windows-only case excluded explicitly | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 5 | file | CLI-provider resolution filters ambient repository PATH then freezes against those roots | 2026-09-07 | agency_runtime/core/cli_transport.py:373-406 |
| 5 | file | Native installer retains ambient marker roots across private launch-CWD preparation and freezing | 2026-09-07 | agency_runtime/core/installer_native.py:240-284 |
| 5 | file | Dashboard manager uses shared roots at discovery/freezing and immediate pre-spawn revalidation | 2026-09-07 | agency_runtime/core/dashboard_service_core.py:842-888 |
| 5 | file | Smoke Node syntax path uses shared discovery, freezing and revalidation | 2026-09-07 | agency_runtime/core/smoke.py:256-281 |
| 5 | file | Explicit fifth-criterion reconciliation preserves current entry points and retired backends | 2026-09-07 | docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md#decision |
| 5 | command-output | Exact deletion commit and current absence are distinguished from surviving launch helpers | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#retired-and-current-surfaces |
| 5 | file | Merged Job B checkpoint records deliberate removal of Agency-owned worker execution | 2026-09-07 | docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md:83-94 |
| 5 | file | Current Rule 5 retains native host ownership of spawning | 2026-09-07 | docs/NORTH_STAR_ACCEPTANCE.md:49-59 |
| 6 | test | Ordinary non-repository absolute PATH resolves the external executable | 2026-09-07 | tests/test_executable_discovery_security.py:112-133 |
| 6 | file | Search keeps absolute non-forbidden entries and deduplicates platform-normalized paths | 2026-09-07 | agency_runtime/core/process_argv.py:261-297 |
| 6 | command-output | Fresh external-PATH positive cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 7 | command-output | 38 discovery, 129 current launch and 24 surviving Git/process cases pass warning-strict | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 7 | command-output | Exact-byte named-spine and DOM reuse are bounded and explicit | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#exact-byte-broader-receipts-and-limits |
| 7 | command-output | Fresh Ruff, documentation, policy, worklog and diff checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#publication-validation |

## Verification

Seven current criteria await isolated candidate-bound checks. ADR-0227
explicitly reconciles only criterion 5; all other original wording remains.
Portable Windows simulations are not native Windows qualification. No builder
verdict is supplied.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-164.1-20260907-99e44725` | `9629588004502213c09224b57e5de6a3d41ca6e92fada105d5ec229b93f47fdf` | 2026-09-07 | process_argv.py:299-333 excludes marker-bearing repository ancestors; test_executable_discovery_security.py:77-110 verifies nested-directory discovery rejects sibling bin and selects the external tool, supported by the cited 38-pass receipt. |
| 2 | satisfied | `AR-164.2-20260907-6529d599` | `3ebaa9bd1d5d5209378550e72367e0d360c7de38f6d5132c7fe322e01550f4fd` | 2026-09-07 | git_runner.py:142-201 excludes repository roots before resolving and invoking Git; test_executable_discovery_security.py:323-351 confirms root discovery from a nested directory selects real Git over repository Git. |
| 3 | satisfied | `AR-164.3-20260907-47c2803f` | `348a0b14cf21b22e7d2a9d3255556403677014557e3c3ff37a83245ff9284896` | 2026-09-07 | process_argv.py:387-455 applies forbidden-root validation to explicit paths and resolver results; lines 757-775 raise OSError for containment, and test_executable_discovery_security.py:136-154 covers both explicit paths and a one-argument resolver. |
| 4 | satisfied | `AR-164.4-20260907-4159c3c4` | `1dca9084a844171a5f894849b4391edf4201c4648aeba274da7e4e59c43d1d56` | 2026-09-07 | process_argv.py shows Windows-aware normalization and lexical/resolved root checks; test_executable_discovery_security.py covers case, drives, PATHEXT and link aliases, with 38 passes recorded in the cited receipt. |
| 5 | absent | `AR-164.5-20260907-494620b7` | `984703bd6bb8a2ce214dd6788db1af40c9c625f0536de88004c9bd8fdeedb0c2` | 2026-09-07 | The four code excerpts show shared-contract integration, but AR-164-executable-boundary-20260907.md only asserts backend removal; no repository snapshot or actual Git output demonstrates their continued absence at the candidate commit. |
| 6 | satisfied | `AR-164.6-20260907-f1b38876` | `6ee68c12f627caa28bd0d07a835b17b3ac1b425e4260816e4c5bbc4790a42270` | 2026-09-07 | process_argv.py:261-297 retains absolute external PATH entries, test_executable_discovery_security.py:112-133 verifies external executable resolution, and the cited focused verification records 38 passing tests. |
| 7 | satisfied | `AR-164.7-20260907-2cd3ee00` | `cf2bde1b5bf53592865732eb019cb9de59d94a97c4cf3e497c387bba6ee7cef5` | 2026-09-07 | AR-164-executable-boundary-20260907.md records 191 focused test passes, Ruff check and format passing for 766 files, strict documentation validation passing for 1180 Markdown files, and scoped git diff --check returning zero. |
