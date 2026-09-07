---
title: "AR-158: Disambiguate multi-surface observation test evidence"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-07
tags: [testing, observability, reliability, performance]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - tests/test_mcp_server.py
  - tests/test_http_server.py
  - tests/test_host_hooks.py
  - tests/test_runtime_observability.py
  - tests/test_store_observability.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-158
priority: p1
tracker_url: null
depends_on: []
blocks: [AR-156]
---

# AR-158: Disambiguate multi-surface observation test evidence

## Problem

Three observability tests select the first `agency_observation` log record and
only afterward assert its surface and operation. Agency intentionally emits
nested Store and transport observations, so load can make a legitimate Store
`slow_query` record precede the surface under test and fail an otherwise-correct
run.

## Current state

September 7 review confirms existing exact MCP and HTTP selectors from
aad2901. Their unrelated Store injection and all-message privacy assertions
remain. The old hook test was deliberately removed by 20f006b6 with retired
child-launch denial; restore observation proof on the current UserPromptSubmit
failure contract, not the removed blocking behavior.

The current three-host fail-open test now captures the actual observation
logger directly, injects a Store event first and selects the exact hook surface/
operation. It verifies content-free degraded/boundary_failure evidence while
the host continues. Fixture-only logger changes restore after each case.
Store slow/busy cases now inject matching unrelated Store events; the busy
query is inside an explicit request boundary and selection requires its exact
request ID. Privacy checks cover all captured Store envelopes. The nested
boundary test preserves correlated Store-before-MCP order despite an unrelated
earlier event. No product or script change.

Thirteen focused cases pass (1.22s). Five MCP/HTTP/three-host cases pass ten
consecutive runs, 50 total, each run 0.63–0.65s. Complete hook-logging/host-hooks/
MCP/runtime-observation/Store-observation package passes 135 with five existing
skips (36.16s). Same-byte production-spine/UI/wheel receipts remain explicit.
Only the obsolete seventh corpus requirement is reconciled under ADR-0105;
first six criteria are unchanged. Seven isolated verdicts remain before closure.

## Historical trigger

AR-156 control run `2c655b34b1e22d55a42b52db93c491f3` rejected one of four
shards. Store initialization took 172.487 ms and emitted
`store/sqlite.commit/degraded/slow_query` before the correct
`mcp/agency.search_agents/ok/completed` record. The test compared the Store
request ID with the MCP result request ID. Production emitted both envelopes
with distinct, correct identities; the failure was ambiguous test selection.
The controller correctly withheld the complete timing artifact.

## Approach

Complete the current bounded test proof, preserving North Star R8 and the
original six product/test requirements. Freeze builder evidence and obtain
seven isolated verdicts before marking done. Do not restore obsolete child
denial or use a whole-corpus rerun as a routine completion gate.

### Original implementation approach

Parse all bounded observation records and select by the surface, operation, and
request ID owned by the assertion. Continue checking every captured observation
for forbidden request content. Inject a valid unrelated Store observation before
each affected MCP, HTTP, and hook action so the regression is deterministic
without depending on machine load or wall-clock thresholds.

Harden lower-risk Store and boundary unit tests at the same seam by filtering
the Agency logger prefix, exact request ID, surface, operation, outcome, and
reason owned by each assertion while preserving intentional Store-before-outer
boundary ordering.

## Dependencies

AR-142 and ADR-0027 define the multi-surface runtime evidence contract. AR-156
owns the load-bearing Windows corpus that exposed the invalid assumption.

## Acceptance

- [ ] MCP evidence selection matches `mcp/agency.search_agents` and the result's
  exact request ID even when a Store observation appears first.
- [ ] HTTP evidence polling waits for the exact HTTP surface, operation, and response
  request ID rather than any observation.
- [ ] Hook evidence selects the exact hook surface and operation.
- [ ] Forbidden request content is absent from every captured observation, not only
  the selected record.
- [ ] Each regression deterministically injects an unrelated valid Store event.
- [ ] Store and runtime-boundary tests retain exact request correlation and ordering
  without depending on the last or first ambient log record.
- [ ] Focused tests pass repeatedly and the named warning-strict production
  spine passes under ADR-0105.

## Requirement reconciliation

Only criterion 7 changes. Original wording: "Focused tests pass repeatedly and
the warning-strict corpus remains green." ADR-0105 makes the complete corpus,
aggregate coverage and interpreter matrix optional owner-requested diagnostics.
Repeated focused tests and the named spine remain required; original criteria
1–6 are unchanged. No exhaustive pass or native Windows proof is implied.

## Historical implementation evidence

The three exact regressions pass together and passed ten consecutive repeated
runs after deterministic unrelated Store injection. Ruff and format checks pass.
Independent review confirmed these were the only first-record selectors with a
real multi-surface ambiguity and identified the lower-risk selectors hardened in
the same slice. Full warning-strict evidence remains required before closure.
Tracker creation remains pending explicit outward authorization.
