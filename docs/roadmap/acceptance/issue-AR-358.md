---
title: "AR-358 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-358
candidate_commit: 37abd00aa4ee2d4e02566f786cac8e9ff750a318
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/428
---

# AR-358 acceptance verification record

Installer trust chains stay trusted and doctor repairs them: builder evidence
cited by the integrator against the merged candidate `37abd00a` (the AR-358
merge `0b04e00d` plus its captured command output); every verdict below comes
from one isolated single-check verifier run (`scripts/verify_acceptance.py`,
codex transport) that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_install_openclaw_plugin calls _normalize_host_trust_chains before session.run("install")` | 2026-09-02 | `agency_runtime/core/installer_registration.py:436-458` |
| 1 | file | `_register_marketplace_host calls it for claude before _ensure_marketplace` | 2026-09-02 | `agency_runtime/core/installer_registration.py:852-867` |
| 1 | file | `_explain_trust_chain_failure names the untrusted chain instead of the host's opaque text` | 2026-09-02 | `agency_runtime/core/installer_registration.py:307-321` |
| 1 | test | `test_the_claude_npm_self_update_break_is_found_and_repaired` | 2026-09-02 | `tests/test_trust_chain_repair.py:57-77` |
| 1 | test | `test_the_openclaw_global_install_break_is_found_and_repaired` | 2026-09-02 | `tests/test_trust_chain_repair.py:78-92` |
| 1 | test | `test_openclaw_2026_8_install_and_enable_carry_capability_consent` | 2026-09-02 | `tests/test_installer_registration.py:1089-1131` |
| 1 | command-output | `pytest: the repaired-tree tests PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-358-pytest-20260902.txt:5-16` |
| 2 | file | `_trust_chain_checks: doctor lists every break, and repairs only with consent` | 2026-09-02 | `agency_runtime/core/doctor.py:823-881` |
| 2 | file | `agency doctor --fix-perms` | 2026-09-02 | `agency_runtime/cli/parser.py:453-464` |
| 2 | file | `repair_trust_chains refuses without consent and refuses unregistered chains` | 2026-09-02 | `agency_runtime/core/trust_chain_repair.py:618-680` |
| 2 | file | `_chmod_verified: never through a link, never a path trusted twice` | 2026-09-02 | `agency_runtime/core/trust_chain_repair.py:458-490` |
| 2 | test | `test_doctor_lists_breaks_and_repairs_them_only_with_consent` | 2026-09-02 | `tests/test_trust_chain_repair.py:190-226` |
| 2 | test | `test_repair_refuses_without_consent_and_outside_the_registry` | 2026-09-02 | `tests/test_trust_chain_repair.py:124-160` |
| 2 | test | `test_doctor_cli_passes_consent_through` | 2026-09-02 | `tests/test_trust_chain_repair.py:227-255` |
| 2 | command-output | `pytest: the doctor consent tests PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-358-pytest-20260902.txt:9-16` |
| 3 | test | `the Claude npm self-update break` | 2026-09-02 | `tests/test_trust_chain_repair.py:57-77` |
| 3 | test | `the OpenClaw global install break` | 2026-09-02 | `tests/test_trust_chain_repair.py:78-92` |
| 3 | test | `the plugin-cache directories that were not owner-private` | 2026-09-02 | `tests/test_trust_chain_repair.py:93-108` |
| 3 | test | `a group-writable ancestor breaks the chain too` | 2026-09-02 | `tests/test_trust_chain_repair.py:109-123` |
| 3 | test | `a symlinked entry is never chmod-ed through` | 2026-09-02 | `tests/test_trust_chain_repair.py:161-175` |
| 3 | file | `_break_kinds: how each measured shape is classified` | 2026-09-02 | `agency_runtime/core/trust_chain_repair.py:425-446` |
| 3 | command-output | `pytest: all three measured shapes PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-358-pytest-20260902.txt:5-16` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 2 | satisfied | `AR-358.2-20260902-b6bb853a` | `5c255283d9a547de0551504c81c04c283b67c0068feeff399680bfd07766418a` | 2026-09-02 | The excerpts show doctor lists breaks without changing modes, --fix-perms supplies consent, repairs are limited to registered chains, and both required tests passed. |
| 3 | satisfied | `AR-358.3-20260902-8f22e0e9` | `07c90e527715a477694bceb7652ca8eb0d5c2fc33a4497bf69cc2cf0a41dda0f` | 2026-09-02 | The cited test excerpts cover all five named regression shapes, and the command-output excerpt records each corresponding test as PASSED with 59 tests passing. |
| 1 | satisfied | `AR-358.1-20260902-350399db` | `28dfb30d68b2e1af1491d09e8195d8d13bbad14bc6575f21536fb93ba10d3a15` | 2026-09-02 | The cited installer excerpts call `_normalize_host_trust_chains` before OpenClaw install and Claude marketplace probing, while the cited Claude broken-tree test repairs group-writable paths, rescans clean, and is recorded as passing. |
