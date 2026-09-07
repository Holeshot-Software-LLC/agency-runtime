---
title: "AR-131 acceptance verification record"
status: active
category: roadmap
created: 2026-09-06
updated: 2026-09-07
tags: [acceptance, verification, mcp, contracts]
related:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-131
candidate_commit: 973acdb991c10e54656990ef0a39db4262adb8be
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-131 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `All eight tool input schemas use the bounded string constructor` | 2026-09-06 | `agency_runtime/server/mcp.py:60-179` |
| 1 | file | `The correlation string bound is the positive integer 512` | 2026-09-06 | `agency_runtime/core/correlation.py:1-40` |
| 1 | file | `The specialist-slug bound is the positive integer 128` | 2026-09-06 | `agency_runtime/core/agent_activation.py:1-17` |
| 1 | test | `Every published string has a positive integer bound` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:328-339` |
| 1 | command-output | `The post-repair MCP-only command passes 126 tests with five existing skips, including the schema-wide invariant` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#current-verification` |
| 2 | test | `Initialized JSON-RPC preflight and status calls reach the handler with their arguments unchanged` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:411-446` |
| 2 | command-output | `Focused MCP/CLI suite records 126 passed with five explicitly scoped pre-existing skips` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#current-verification` |
| 3 | file | `Both host schemas use a shared host-string constructor imported from the host registry` | 2026-09-06 | `agency_runtime/server/mcp.py:60-179` |
| 3 | file | `Supported hosts alias the canonical execution-host set` | 2026-09-06 | `agency_runtime/core/host_control.py:1-25` |
| 3 | file | `The canonical execution set contains Codex, Claude, OpenClaw, Hermes and ZCode` | 2026-09-06 | `agency_runtime/core/host_capabilities.py:19-26` |
| 3 | test | `Every host property is checked directly against the canonical tuple` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:328-339` |
| 4 | file | `Public delegation admission checks every identifier before forwarding unchanged values to Store; master-off and active-turn guards remain` | 2026-09-06 | `agency_runtime/__init__.py:310-421` |
| 4 | file | `Shared bounds and exact public validation reject truncation, coercion, control characters and whitespace normalization; native observation normalization is separate` | 2026-09-06 | `agency_runtime/core/delegation_status.py:1-48` |
| 4 | file | `The public active-turn guard validates both correlation identifiers before lookup` | 2026-09-06 | `agency_runtime/core/turn_correlation.py:1-49` |
| 4 | file | `Correlation validation checks string type, printable Unicode and the 512-byte UTF-8 limit` | 2026-09-06 | `agency_runtime/core/correlation.py:1-40` |
| 4 | test | `Shared limits and real-preflight fixture; an oversized work-unit alias cannot alter the existing record; noncanonical fields fail without rows` | 2026-09-06 | `tests/test_public_api.py:28-131` |
| 4 | test | `Every ASCII and Unicode maximum-sized public identifier round-trips through a real completed event; supported canonical spaces and optional empties persist unchanged` | 2026-09-06 | `tests/test_public_api.py:134-167` |
| 4 | command-output | `Public admission has 13 passing cases; the alias regression failed before repair; exact commands, scope and the unrelated broad-suite failure are recorded` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#current-verification` |
| 4 | file | `The low-level native-observation path still applies defensive normalization before its transaction; admitted public identifiers already match that form` | 2026-09-06 | `agency_runtime/core/store/evidence.py:3590-3697` |
| 5 | test | `Published tool names exactly equal lookup and handler names; generated status skills use valid read-only registry calls on all hosts` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:342-359` |
| 5 | file | `The complete published tool registry and derived name lookup contain the same eight names` | 2026-09-06 | `agency_runtime/server/mcp.py:91-181` |
| 5 | file | `The dispatch registry contains precisely the eight published tool handlers` | 2026-09-06 | `agency_runtime/server/mcp_tools.py:364-385` |
| 5 | file | `Generated control skills derive conversation forms from runtime constants and call the registered host-status tool` | 2026-09-06 | `agency_runtime/core/installer_payloads.py:605-637` |
| 5 | command-output | `The post-repair 126-pass MCP package executes exact registry parity and all five generated-host skill cases` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#current-verification` |
| 5 | command-output | `Installed Codex control skill is byte-identical to the current generator, without an installation or activation claim` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#installed-skill-file-check` |
| 6 | test | `Malformed, unknown, oversized and unexpected-argument calls fail at protocol dispatch` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:256-325` |
| 6 | test | `Model-facing host mutation and caller-supplied finalization host/model spoofing are rejected` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:449-486` |
| 6 | test | `All three retired delegation tools reject before Store access` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:362-385` |

## Verification

First-candidate verdicts are preserved verbatim at 6a139e23. The six independent
runs below verify repaired candidate 973acdb9; the isolated runner supplied
every verdict. No prior verdict was relabeled as a pass.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-131.1-20260907-be0d42d1` | `c9fc18d15884a7003868b3c707d1380b2f3852aea5e3136e4232d0d6d4c9c536` | 2026-09-07 | mcp.py:60-179 gives every string property an explicit maxLength via _string; correlation.py and agent_activation.py define positive bounds, and the cited schema invariant and passing MCP verification support validity. |
| 2 | satisfied | `AR-131.2-20260907-d6b3a064` | `0cd489105b9217132791a909188fe2d6efbdf0823b5edea7be7330429b838bf1` | 2026-09-07 | tests/test_mcp_protocol_hardening.py:411-446 exercises initialized MCPServer JSON-RPC dispatch for preflight and status, asserting unchanged handler arguments and successful responses; the cited verification record reports 126 passed. |
| 3 | satisfied | `AR-131.3-20260907-fef0402e` | `97ce6c4b543881070f18d21a8e9f7eeb99731d0082ae91bf6d612af995a6ce30` | 2026-09-07 | mcp.py uses _host_string() for host schemas, host_control.py aliases SUPPORTED_HOSTS to the five-entry EXECUTION_HOSTS tuple, and test_mcp_protocol_hardening.py checks every published host enum against that vocabulary. |
| 4 | satisfied | `AR-131.4-20260907-4123af82` | `8766124d0bf06e368379381c15968f29f6c20f9db25117a213d500d4a21518bb` | 2026-09-07 | Public validation in agency_runtime/__init__.py and delegation_status.py rejects identifiers that normalization would alter, while tests/test_public_api.py demonstrates exact ASCII and Unicode maximum-length round trips and rejection without writes. |
| 5 | satisfied | `AR-131.5-20260907-c19d7a01` | `140a5bdbd06e45d28cb750d8e6c0a104b097f54b5e683abb3119487c9f710979` | 2026-09-07 | mcp.py and mcp_tools.py show identical eight-tool registries; installer_payloads.py and tests/test_mcp_protocol_hardening.py demonstrate valid generated skill calls for every host, supported by the cited 126-pass MCP verification. |
| 6 | satisfied | `AR-131.6-20260907-ad02bf8b` | `e343187b5f5296301166567a1a6201f6e47a28b71cb4206024b8358d9fcbfc89` | 2026-09-07 | tests/test_mcp_protocol_hardening.py:256-325, 449-486, and 362-385 cover rejection of invalid, unknown, oversized, mutation, spoofed-identity, and retired-tool requests at dispatch with an unusable Store. |
