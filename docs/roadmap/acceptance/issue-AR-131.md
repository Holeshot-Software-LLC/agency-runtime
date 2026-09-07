---
title: "AR-131 acceptance verification record"
status: active
category: roadmap
created: 2026-09-06
updated: 2026-09-06
tags: [acceptance, verification, mcp, contracts]
related:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-131
candidate_commit: fb2e4e2379939c7525018a14b2c54f8f15b168fb
evidence_cutoff: 2026-09-06
tracker_url: null
---

# AR-131 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `All eight tool input schemas use the bounded string constructor` | 2026-09-06 | `agency_runtime/server/mcp.py:60-179` |
| 1 | test | `Every published string has a positive integer bound` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:328-339` |
| 2 | test | `Initialized JSON-RPC preflight and status calls reach the handler with their arguments unchanged` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:411-446` |
| 2 | command-output | `Focused MCP/CLI suite records 126 passed with five explicitly scoped pre-existing skips` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#current-verification` |
| 3 | file | `Both host schemas use a shared host-string constructor imported from the host registry` | 2026-09-06 | `agency_runtime/server/mcp.py:60-179` |
| 3 | file | `Supported hosts alias the canonical execution-host set` | 2026-09-06 | `agency_runtime/core/host_control.py:1-25` |
| 3 | file | `The canonical execution set contains Codex, Claude, OpenClaw, Hermes and ZCode` | 2026-09-06 | `agency_runtime/core/host_capabilities.py:19-26` |
| 3 | test | `Every host property is checked directly against the canonical tuple` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:328-339` |
| 4 | test | `Canonical maximum-sized delegation identifiers round-trip through a real Store; oversized correlation IDs are rejected without a second record` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:388-408` |
| 4 | file | `Remaining Store path uses shared bounds before insertion; internal normalization still exists for noncanonical input` | 2026-09-06 | `agency_runtime/core/store/evidence.py:3590-3697` |
| 4 | file | `Shared field limits and normalization are explicit; canonical boundary-sized identifiers are unchanged` | 2026-09-06 | `agency_runtime/core/delegation_status.py:8-32` |
| 4 | test | `The old model-facing delegation admission path is absent: all three retired names reject before Store access` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:362-385` |
| 5 | test | `Published tool names exactly equal lookup and handler names; generated status skills use valid read-only registry calls on all hosts` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:342-359` |
| 5 | file | `Generated control skills derive conversation forms from runtime constants and call the registered host-status tool` | 2026-09-06 | `agency_runtime/core/installer_payloads.py:605-637` |
| 5 | command-output | `Installed Codex control skill is byte-identical to the current generator, without an installation or activation claim` | 2026-09-06 | `docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md#installed-skill-file-check` |
| 6 | test | `Malformed, unknown, oversized and unexpected-argument calls fail at protocol dispatch` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:256-325` |
| 6 | test | `Model-facing host mutation and caller-supplied finalization host/model spoofing are rejected` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:449-486` |
| 6 | test | `All three retired delegation tools reject before Store access` | 2026-09-06 | `tests/test_mcp_protocol_hardening.py:362-385` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | absent | `AR-131.1-20260906-cc093673` | `881af29ee366c21b1266f28abdb22ec91d21242a0da2028911e24061951531ec` | 2026-09-06 | mcp.py:60-179 explicitly bounds every string, but omits the values of MAX_CORRELATION_ID_BYTES and MAX_AGENT_SLUG_CHARS; tests/test_mcp_protocol_hardening.py:328-339 shows assertions without results confirming valid bounds. |
| 2 | satisfied | `AR-131.2-20260906-ec184f4f` | `a68dbf935e1eb406b77196ca51d74ed85b7a445e8163b9210767b03651c8c5c5` | 2026-09-06 | tests/test_mcp_protocol_hardening.py:411-446 exercises initialized MCPServer JSON-RPC dispatch for preflight and host_status and verifies unchanged handler arguments; the cited verification record reports 126 passing tests. |
| 3 | satisfied | `AR-131.3-20260906-691c2b18` | `1ecdf360f54dc68b9303c5f5a08a76f28e6e457c065287a091127cc6da808e45` | 2026-09-06 | mcp.py uses _host_string() for host schemas, host_control.py aliases SUPPORTED_HOSTS to the five-entry EXECUTION_HOSTS tuple, and test_mcp_protocol_hardening.py checks every host enum against that vocabulary. |
| 4 | contradicted | `AR-131.4-20260906-dbded3f7` | `49e4068d425700dba17a27cc870649cc2b94f4c7cbfb678dcd0f426bdc4566e6` | 2026-09-06 | record_delegation in evidence.py applies bounded_delegation_field, whose delegation_status.py implementation slices identifiers to maximum length without rejecting oversized input; the boundary-only test does not cover this truncation. |
| 5 | absent | `AR-131.5-20260906-84d6e9ed` | `44f7f2e6c5d07b57dc5defe3dffbf52ca83d738efdf58ea5cea0621dca1aba1e` | 2026-09-06 | tests/test_mcp_protocol_hardening.py asserts registry equality, but no test results or registry definitions are shown; the generator and reported Codex file comparison alone cannot establish exact agreement. |
| 6 | satisfied | `AR-131.6-20260906-639d8a0b` | `92dd3110a4f2ec5508c95f063aea5767e09faba9dfbb3eb75c496bbdda84c77a` | 2026-09-06 | tests/test_mcp_protocol_hardening.py:256-325, 362-385, and 449-486 assert rejection of invalid, unknown, oversized, mutation, and spoofed requests at dispatch, using a Store without methods. |
