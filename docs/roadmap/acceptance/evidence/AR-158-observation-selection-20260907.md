---
title: "AR-158 current multi-surface observation selection"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [observability, tests, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-158 current observation-selection evidence

## Existing interfaces and restored current hook proof

Baseline main ea6864b1 (PR #709), merge ledger 38f2a733. MCP and HTTP
regressions already inject a real unrelated Store boundary before the action,
parse all observation messages, and select their exact surface, operation and
returned request ID. Their privacy assertions inspect every captured observation.
HTTP polls until its exact matching response observation arrives.

Original hook proof was removed by 20f006b6 when the old planned-child denial
was retired. The current UserPromptSubmit integrity-failure case, parameterized
over Codex/ZCode/Claude, now supplies that proof under North Star R8: unavailable
Agency does not block the host. A test-only bridge failure returns an empty
JSON response and bounded type-only stderr, with one actual hook observation
marked degraded/boundary_failure. No old child-denial policy is restored.

The test attaches capture directly to the observation logger so an earlier
file sink disabling root propagation cannot hide evidence. Handlers/propagation
are restored by monkeypatch, and ambient opt-in file output is disabled only
inside the test. A real Store boundary is first; the selected hook has a
different ID and the exact host.userpromptsubmit operation. Private prompt and
error markers are absent from every captured observation and stderr.

## Store and nested boundary correlation

Slow and busy Store tests inject a valid unrelated event with the same Store
operation and reason as the expected event. Selection requires the tested
boundary's request ID, not the first or last ambient match. The busy query now
runs inside an explicit HTTP boundary; all captured Store envelopes are checked
for SQL-value/path sentinels, not just the selected envelope.

The nested runtime test injects another unrelated Store boundary, then selects
only the current request's Store/MCP envelopes. It preserves Store-before-MCP
ordering, exact correlation and the outer outcome; its positional assertions
apply only after exact-ID filtering. Existing late-correlation and exception
tests retain exact boundary IDs, surface and operation.

## Fresh focused verification

```bash
PYTHONPATH=. python -m pytest \
  tests/test_mcp_server.py::test_mcp_tool_result_and_logs_share_content_free_request_identity \
  tests/test_http_server.py::test_http_response_exposes_safe_request_id_and_content_free_observation \
  tests/test_host_hooks.py::test_hook_boundary_publishes_prompt_when_preflight_integrity_fails \
  tests/test_runtime_observability.py tests/test_store_observability.py -q -W error
```

Thirteen passed, no failures/skips/deselections, 1.22s. The first three node
selectors above (five parameterized cases) then ran in ten consecutive fresh
pytest processes: all 50 passed, each run 0.63–0.65s, no failure or skip.
Injection is deterministic and does not require a loaded machine or benchmark.

```bash
PYTHONPATH=. python -m pytest tests/test_hook_logging.py tests/test_host_hooks.py \
  tests/test_mcp_server.py tests/test_runtime_observability.py \
  tests/test_store_observability.py -q -W error
```

Complete five-module package: 135 passed, five existing skips, zero failures/
deselections, 36.16s. This includes the full changed modules, real hook subprocess
contracts, MCP dispatch and logger-sink lifecycle. It is not a native host canary.
Ruff check/format pass, 766 files; no skips or xfails were added.

## Exact-byte broader receipts

```bash
git diff --exit-code dccb4e85 -- agency_runtime scripts
git diff --exit-code a35657e1 -- tests ':!tests/test_host_hooks.py' ':!tests/test_runtime_observability.py' ':!tests/test_store_observability.py'
```

Both return zero. The three changed test files are not members of the named
29-module production spine (host_hooks belongs to the separate matrix-evidence
list). Reuse [AR-156's named spine receipt](AR-156-verification-workflow-20260907.md#fresh-verification):
1085 passed, three existing skips, 68.41s. The unchanged UI remains 188 passed,
production coverage 96.93/86.71/95.71. These are same-byte reuse, not new runs.
The exact clean dccb4e85 wheel's ten matching assets and 21 loaded-browser
checks also apply to unchanged product bytes; no installation was repeated.

## Scope and policy

Only criterion 7 is explicitly reconciled under ADR-0105; the first six and
original seventh wording remain. No production/script change, threshold
relaxation, new native Windows execution, exhaustive corpus/matrix, hosted
dispatch or normal-session activation claim. The builder records evidence only;
seven isolated verdicts must precede closure.
