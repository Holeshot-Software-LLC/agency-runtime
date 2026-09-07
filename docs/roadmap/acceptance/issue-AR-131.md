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
candidate_commit: pending
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

First-candidate verdicts are preserved verbatim at 6a139e23. This repaired
candidate starts an empty verification section; only the isolated runner
supplies its new verdicts. No prior verdict is relabeled as a pass.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
