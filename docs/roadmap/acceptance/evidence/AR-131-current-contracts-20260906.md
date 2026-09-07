---
title: "AR-131 current MCP and CLI contract evidence"
status: active
category: roadmap
created: 2026-09-06
updated: 2026-09-06
tags: [acceptance, mcp, cli, contracts]
related:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/issue-AR-131.md
  - tests/test_mcp_protocol_hardening.py
  - agency_runtime/server/mcp.py
  - agency_runtime/server/mcp_tools.py
  - agency_runtime/core/installer_payloads.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-131 current MCP and CLI contract evidence

## Scope

Review base c1c5d9d9, September 6 local date. The first test-only candidate
fb2e4e23 added ten cases and strengthened the old host-enum assertion. The
repaired candidate additionally enforces exact public Python delegation
identifier admission with 13 regression cases. Native observations retain
their defensive internal normalization. This tests public contracts, not live
inference nomination, native child execution, Windows-attested roots or
five-host activation. First candidate verdicts are preserved at 6a139e23.

## Current verification

Repaired public-entry regression command:

```bash
python -m pytest tests/test_public_api.py -k public_delegation -q -W error --tb=short
```

Result: **13 passed, 22 deselected in 20.35s**. Each case uses a real temporary
Store and an actual trivial preflight to establish its active turn. The alias
test failed before repair (`DID NOT RAISE ValueError`, 1.93s): an overlong
work-unit ID could merge into an existing prefix-matched event. Rejection now
leaves that existing row unchanged. All seven bounded identifier fields reject
oversize/type/whitespace/control-character inputs without recording a row;
trace/session IDs retain exact whitespace and UTF-8 byte bounds. ASCII and
Unicode maximum-sized IDs round-trip through the completed-event path. Empty
optional fields and canonical single interior spaces remain supported.

Post-repair named spine: **1085 passed, 3 skipped in 68.60s**. UI: **138 passed**,
zero failed/skipped (190.76ms). Ruff check/format pass for all 764 files. The
current-source routing evaluator again passes all gates. The expanded
nine-module command below has **380 passed, 1 failed, 8 skipped in 59.71s**:

```bash
python -m pytest tests/test_public_api.py tests/test_evidence_integrity.py \
  tests/test_mcp_protocol_hardening.py tests/test_mcp_server.py \
  tests/test_mcp_cli_dispatch_tables.py tests/test_cli_parser_contract.py \
  tests/test_preflight_bounds.py tests/test_runtime_control.py \
  tests/test_security_turn_boundaries.py -q -W error --tb=short -rs
```

The sole failure is the unchanged
`test_public_route_repairs_legacy_fallback_roster_without_opening_turns`:
it also fails alone on untouched main c1c5d9d9 (2.04s). The offline fixture
expects fallback companions even though `selector/pipeline.py` suppresses them
after inference failure. AR-176 records its repair; the test was not changed,
skipped or called green. Existing skips are five full-inference cases, one
Windows-attested root, one Linux workforce-stub case and one Windows lock case.
The initial ungrouped invalid-input matrix also exposed this same failure
(170 passed/one failed/one skip, 118.89s). Grouping invalid values per field
retains every assertion while avoiding repeated expensive preflight setup.

Post-repair `agency eval decision-conformance --repository . --json` also
passes: baseline exit 0 in 97,977 ms; **184/184 protected mutations killed**,
zero survived/invalid and `source_unchanged: true`. It ran through the
current-source CLI with a process-local private umask. This is curated
decision sensitivity, not an exhaustive mutation or release certificate.

MCP-only command, rerun after the repair:

```bash
python -m pytest tests/test_mcp_protocol_hardening.py \
  tests/test_mcp_server.py tests/test_mcp_cli_dispatch_tables.py \
  tests/test_cli_parser_contract.py -q -W error --tb=short -rs
```

Using an isolated development interpreter with this worktree first on
PYTHONPATH: **126 passed, 5 skipped in 5.00s** (first candidate: 6.06s). The five existing skips are four
ADR-0087 full-inference nomination/delivery cases and one Codex-attested Windows
task-root case. They were not added or changed by this package. Before the ten
new cases, the same package passed 116 with the same five skips in 5.54s.

The named 29-file production spine passed 1075 tests with three existing skips
in 67.21s before the test-only additions. The fresh post-addition spine passed
1085 tests with the same three skips in 69.18s. Dashboard UI: 138 passed, zero
failed/skipped. Ruff
checks and format checks pass for all 764 Python files. No exhaustive corpus,
coverage/interpreter matrix, hosted dispatch or Windows execution was run.

The current-source routing evaluator also passes all gates (45 recall, 30
policy, 22 delegation cases). Its synthetic inference-receipt/cache timings
are deterministic recall diagnostics, not end-to-end live staffing latency.
The current-source decision-conformance evaluator also returned exit 0,
`passed: true`, `status: passed`, and `source_unchanged: true`; its baseline
passed in 99,281 ms. This receipt precedes the pending admission repair.

## First isolated review

Candidate fb2e4e2379939c7525018a14b2c54f8f15b168fb:
`python scripts/verify_acceptance.py --issue AR-131 --all` returned exit 2
without writing verdicts. Read-only transport inspection found Claude refused
as untrusted because its executable's parent namespace permits substitution.
Codex was installed, authenticated and usable; the supported `--provider codex`
invocation returned exit 0 and wrote six independent criterion verdicts.

Criteria 2/3/6 are satisfied. Criteria 1/5 lack the constants/registry definitions
and per-criterion passing-command citations in their supplied excerpts.
Criterion 4 is contradicted: internal Store normalization slices oversized
identifiers, and a test at the maximum alone does not prove exact admission.
The public Python facade admitted those values. The first verdicts remain
preserved at 6a139e23 before any candidate/evidence replacement. The repair and
red/green evidence are above. Freeze this new candidate for all six criteria;
verifier verdicts are not hand-edited. The current contract concerns accepted
public requests, not arbitrary low-level administrative/native observations.

## Observed boundaries

- Every published string parameter is explicitly bounded. Both `host` fields
  are generated by `_host_string` from the single supported-host tuple.
- Initialized JSON-RPC preflight/status calls reach the handler; malformed,
  unknown, oversized and model-facing control-mutation calls are rejected.
- Published tool names, lookup names and handler names are exactly equal,
  without duplicates. Each generated host-control skill names only the valid
  read-only `agency.host_status` invocation for that host.
- All three former delegation-branch tool names are absent and return unknown
  at protocol/direct dispatch before Store access, including an oversized ID.
  They were removed at eab8c085, not by this package.
- Maximum-sized canonical trace/session/work-unit/agent/backend/worker/native-run
  identifiers persist exactly in a real temporary Store. Oversized correlation
  IDs fail before a second record is written. This is not a promise that the
  internal normalizer preserves arbitrary noncanonical inputs.

## Installed skill file check

A read-only `cmp` between the current `agency_control_skill("codex")` renderer
and the installed Codex cache's `skills/agency/SKILL.md` returns exit 0. The
renderer emits the registered status call and directs on/off requests to the
owner CLI/dashboard. No file is refreshed or edited by this comparison.

This resolves the record's historical stale-skill-file observation on this
machine, not Codex hook trust, current-session header correlation or live
staffing. Those remain separate evidence obligations. No human trust, gateway
restart, credential creation or permission change was performed.

After the comparison, a runtime-requested `agency install --agent codex` was
attempted once from main. It returned exit 1 with files registered but
activation required, hook trust unverified and a mixed installed-projection
warning (the CLI uses the AR-348 package, while another installed projection
still references the AR-271 package). No trust bypass, repeated install,
OpenClaw replacement or live-success claim followed.
