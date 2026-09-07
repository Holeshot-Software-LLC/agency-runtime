---
title: "AR-131: Complete MCP and CLI host contracts"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-06
tags: [mcp, cli, host-integrations, schema, compatibility]
related:
  - agency_runtime/server/mcp.py
  - agency_runtime/server/mcp_tools.py
  - agency_runtime/core/host_control.py
  - tests/test_mcp_protocol_hardening.py
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/acceptance/issue-AR-131.md
  - docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-131
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-131: Complete MCP and CLI host contracts

## Problem

Valid host-bearing MCP calls fail the server's own fail-closed string-schema
validator because their `host` fields omit `maxLength`. Independently copied
host enums omit ZCode and can drift from the canonical supported-host set.
Delegation schema maxima also exceed the Store's canonical identifier bounds.

## Current state

September 6 reconciliation: the original schema/dispatch repair is implemented.
Current MCP definitions and handlers agree on eight tools; every string has an
explicit bound and both host-bearing schemas use the canonical five-host set.
Valid preflight/status calls pass through initialized protocol dispatch. Owner
CLI/dashboard authority and read-only MCP control authority follow ADR-0117,
not the superseded owner-presence proposal.

The three model-facing delegation-reporting tools were deliberately removed
at eab8c085 under the native-host delegation rule. Do not restore them to test
the old surface. Current regressions prove all three fail before Store access;
canonical bounded identifiers round-trip through the remaining Store record
path. This does not claim arbitrary noncanonical internal Store inputs are
accepted unchanged: the internal normalizer still exists.

Ten additional regression cases check registry/handler parity, all five
generated status skills, retired-tool rejection, and maximum-sized canonical
identifier persistence. The older host-enum test now examines every `host`
property directly instead of skipping an enum when it already disagrees.
The focused MCP/CLI package passes 126 tests with five pre-existing skips
(6.06s). The installed Codex control skill matches the current generator
byte-for-byte; this is file evidence, not hook trust or live activation.

Original six acceptance criteria remain unchanged. Candidate-bound isolated
verification is pending; this record is not done until those verdicts exist.
No fresh installation, Windows execution or live staffing run is part of the
bounded contract review. This pre-tracker record does not need a new tracker.

Original July reproduction:

Protocol dispatch of valid `agency.preflight` and `agency.host_status` requests
with `host="codex"` returns an error before the handler. Direct-handler tests
hide the defect. Model-callable host mutation is also incompatible with the
authority decision in AR-128.

## Approach

The original implementation approach was:

Generate read-only host and delegation tool schemas from shared constants, add
explicit bounds to every string property, remove model-callable mutations, and
add protocol-level success tests plus a schema-wide invariant test. Reconcile
CLI, HTTP, MCP, and generated skill documentation from one tool registry.

Current verification preserves purpose-specific surfaces: generated control
skills invoke the registered read-only status tool and direct operators to
owner CLI controls, not to an invented model-facing mutation tool. Freeze the
current source/test evidence, run one isolated verifier per original criterion,
and only then determine completion. No runtime code change is needed for the
schema defect that motivated this record.

## Dependencies

AR-128's historical mutation work is governed by the current ADR-0117 authority
split. AR-135 owns ZCode installation/live behavior, which is not inferred from
these protocol tests.

## Acceptance

- [ ] Every published MCP string property has an explicit valid maximum length.
- [ ] Valid preflight and status requests dispatch through the real protocol.
- [ ] All read-only host schemas derive from the canonical five-host set.
- [ ] Accepted delegation identifiers persist exactly without truncation.
- [ ] Generated tool and skill surfaces match the runtime registry exactly.
- [ ] Invalid, unknown, oversized, and mutation requests fail closed.

## Implementation evidence

The following is the historical implementation account. Its installation note
is not a current observed failure; the current Codex skill comparison is above.

All published MCP strings are bounded, host schemas derive from the canonical
five-host registry, delegation bounds match exact Store persistence limits, and
protocol-level preflight/status requests now dispatch successfully. Host
mutation and caller-supplied finalize host/model fields are absent, noncanonical
identifiers fail before Store normalization, generated skills match the
read-only registry, and status no longer exposes an absolute database path.
Fresh installation is still required to replace the stale installed skill.
