---
title: "AR-158 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, observability]
related:
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-158
candidate_commit: 95085a3008389fadf8c4c99123cf3eacfc8e1925
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-158 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | MCP injects unrelated Store evidence first and selects exact mcp/agency.search_agents and returned request ID | 2026-09-07 | tests/test_mcp_server.py:140-183 |
| 1 | command-output | MCP case passes in the 13-case focus and ten fresh five-case repetitions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 2 | test | HTTP polls for its exact surface, operation and response request ID after Store injection | 2026-09-07 | tests/test_http_server.py:1181-1226 |
| 2 | command-output | HTTP identity case passes in the focus and all ten repeated processes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 3 | test | Each current host prompt-failure case selects the exact hook surface and host.userpromptsubmit operation | 2026-09-07 | tests/test_host_hooks.py:2362-2450 |
| 3 | file | Hook entry normalizes its operation and opens the actual hook observation boundary | 2026-09-07 | agency_runtime/adapters/hooks.py:3716-3765 |
| 3 | command-output | Codex, ZCode and Claude cases pass repeatedly and in the complete host-hook module | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 4 | test | MCP checks forbidden request-ID content in every captured observation message | 2026-09-07 | tests/test_mcp_server.py:140-183 |
| 4 | test | HTTP checks its private path against every captured observation during matching polling | 2026-09-07 | tests/test_http_server.py:1181-1226 |
| 4 | test | Hook checks private prompt/error sentinels across all observations and stderr | 2026-09-07 | tests/test_host_hooks.py:2430-2450 |
| 4 | test | Store slow and busy cases check all captured envelopes for private SQL values and paths | 2026-09-07 | tests/test_store_observability.py:36-115 |
| 4 | file | Runtime envelope serializes bounded metadata rather than input content | 2026-09-07 | agency_runtime/core/observability.py:106-163 |
| 4 | command-output | Full focused and broad observation checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 5 | test | MCP creates a valid Store boundary before tool dispatch | 2026-09-07 | tests/test_mcp_server.py:140-183 |
| 5 | test | HTTP creates a valid Store boundary before the real request | 2026-09-07 | tests/test_http_server.py:1181-1226 |
| 5 | test | Hook creates a Store boundary first and verifies its ID differs from the selected hook record | 2026-09-07 | tests/test_host_hooks.py:2385-2450 |
| 5 | command-output | Deterministic injection cases pass ten independent repetitions without requiring machine load | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 6 | test | Slow Store test filters exact request ID despite a matching unrelated earlier event | 2026-09-07 | tests/test_store_observability.py:36-67 |
| 6 | test | Busy Store test enters an explicit boundary and selects its exact ID rather than the last ambient match | 2026-09-07 | tests/test_store_observability.py:70-115 |
| 6 | test | Nested boundary preserves correlated Store-before-MCP order after excluding an unrelated event | 2026-09-07 | tests/test_runtime_observability.py:89-123 |
| 6 | test | Late correlation and exception evidence select their exact boundary IDs and surface/operation | 2026-09-07 | tests/test_runtime_observability.py:126-168 |
| 6 | command-output | Complete Store and runtime-observation modules pass within both focused and broader checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 7 | command-output | Focused 13 pass; all ten five-case repetitions pass; broad package 135 pass/five existing skips | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#fresh-focused-verification |
| 7 | command-output | Exact-byte binding reuses the unchanged named 29-module warning-strict spine | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md#exact-byte-broader-receipts |
| 7 | command-output | Named spine receipt records 1085 passes and three existing skips | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md#fresh-verification |
| 7 | file | Existing bounded-delivery policy makes exhaustive corpus/coverage/matrix optional diagnostics | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |

## Verification

Pending seven isolated single-criterion verifier results.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
