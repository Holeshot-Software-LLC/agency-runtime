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
candidate_commit: pending
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
