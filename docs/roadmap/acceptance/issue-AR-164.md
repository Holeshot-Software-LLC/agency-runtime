---
title: "AR-164 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, executables, security]
related:
  - docs/roadmap/acceptance/evidence/AR-164-backend-tree-20260907.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-164
candidate_commit: 2a7c20c551aa357b07d51753622879322c5803d4
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
| 5 | command-output | Actual full candidate directory listing and deletion-status output demonstrate continued absence of retired modules | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-backend-tree-20260907.md#candidate-tree-snapshot |
| 5 | file | Merged Job B checkpoint records deliberate removal of Agency-owned worker execution | 2026-09-07 | docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md:83-94 |
| 5 | file | Current Rule 5 retains native host ownership of spawning | 2026-09-07 | docs/NORTH_STAR_ACCEPTANCE.md:49-59 |
| 6 | test | Ordinary non-repository absolute PATH resolves the external executable | 2026-09-07 | tests/test_executable_discovery_security.py:112-133 |
| 6 | file | Search keeps absolute non-forbidden entries and deduplicates platform-normalized paths | 2026-09-07 | agency_runtime/core/process_argv.py:261-297 |
| 6 | command-output | Fresh external-PATH positive cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 7 | command-output | 38 discovery, 129 current launch and 24 surviving Git/process cases pass warning-strict | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#fresh-focused-verification |
| 7 | command-output | Exact-byte named-spine and DOM reuse are bounded and explicit | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#exact-byte-broader-receipts-and-limits |
| 7 | command-output | Fresh Ruff, documentation, policy, worklog and diff checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md#publication-validation |

## Verification

All seven current criteria satisfy at 2a7c20c551aa357b07d51753622879322c5803d4
in the second and final isolated review. All first verdicts remain at 6ac3b1aa;
none was carried forward. This candidate adds actual tree/deletion output for
criterion 5 without changing any criterion or product byte.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-164.1-20260907-d8d7011b` | `d3f487259b73b7c90af7df24d1f7c0f6ffbe4d023322d6f81af199cfd0da5b9c` | 2026-09-07 | process_argv.py:299-333 excludes marker-bearing repository ancestors; test_executable_discovery_security.py:77-110 verifies nested discovery rejects sibling bin and selects the external tool, with 38 passing tests recorded in the cited receipt. |
| 2 | satisfied | `AR-164.2-20260907-407b48f8` | `c1c08fde0be7e9d478e32ec0250fe530319da64e4bc7566915883e2a743e987c` | 2026-09-07 | git_runner.py:142-201 excludes repository roots before resolving and invoking Git, and test_executable_discovery_security.py:323-351 verifies initial root discovery selects external Git despite repository Git preceding it on PATH. |
| 3 | satisfied | `AR-164.3-20260907-24ffe924` | `42c2d9452e26ee6d24d720f2a22eac25b555959d707b3e28b09867f33b674232` | 2026-09-07 | process_argv.py:387-455 applies forbidden-root validation to explicit paths and resolver results; lines 757-775 raise OSError for forbidden artifacts, and test_executable_discovery_security.py:136-154 covers both explicit and one-argument resolver rejection. |
| 4 | satisfied | `AR-164.4-20260907-34b95919` | `ac6d3ee2a941e0aee2966235b7ed48602f58a901c626a450312ecee3a4e5ffb2` | 2026-09-07 | process_argv.py shows Windows normalization and lexical/resolved root checks; security tests cover mixed-case CMD paths, PATHEXT rejection and link aliases, with 38 passes recorded in the focused verification receipt. |
| 5 | satisfied | `AR-164.5-20260907-b95ec770` | `8d7a941273c342fed5afb332664304d004311198abdf5e876ddc27f6c43ec40d` | 2026-09-07 | The four launch-path excerpts use shared executable preparation and freezing, while AR-164-backend-tree-20260907.md supplies the retired-module absence listing and unchanged implementation binding. |
| 6 | satisfied | `AR-164.6-20260907-f7f95cae` | `d70df126f7897e202251e9f4def4e028f20cc701628c0cac0141807100a8d0c5` | 2026-09-07 | The external-PATH test in tests/test_executable_discovery_security.py:112-133 asserts successful resolution, process_argv.py:261-297 retains absolute external entries, and the focused verification receipt reports 38 passing tests. |
| 7 | satisfied | `AR-164.7-20260907-7fb9c58b` | `cebfcb7a12850c47babfd2842c10ac05675eceaf9c009e32bfedd8fe4b47c7c7` | 2026-09-07 | The cited AR-164 receipt records 38, 129, and 24 passing focused tests, passing Ruff check and format for 766 files, strict documentation validation for 1180 Markdown files, and a zero-result scoped git diff --check. |
