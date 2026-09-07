---
title: "Reject lossy public delegation identifiers"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, api, delegation, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/issue-AR-131.md
  - docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 973acdb991c10e54656990ef0a39db4262adb8be
short: 973acdb9
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
---

# Worklog: exact public delegation admission

## Purpose and approach

The first isolated AR-131 review exposed a real remaining public admission
gap. A different overlong work-unit ID was accepted and could update an
existing prefix-matched delegation event. The new regression failed before
repair. Validate all public identifiers against their shared Store bounds and
canonical form before forwarding the original values to Store. Correlation
IDs retain byte-based UTF-8 limits and must not need trimming.

## Decisions and alternatives

Enforce the existing exact-public-identifier requirement, not a new staffing
or architectural policy. Retain the intentionally normalizing low-level native
observation path and its existing tests. Do not restore the retired MCP
delegation tools or change routing, model authority, installer trust or worker
selection. Preserve master-off and active-turn admission guards.

First-candidate verdicts are permanently preserved at 6a139e23. The repaired
candidate begins a new empty verification section rather than relabeling old
verdicts. The schema correctly rejects carrying old digests into new evidence;
it also caught an out-of-range source citation, too many builder rows and a
short capsule ledger SHA during draft preparation. Those drafts are corrected;
the builder never supplies its own acceptance verdict.

## Verification

- New public-admission package: 13 passed, 22 deselected (20.35s), real Store
  and trivial preflight; ASCII/Unicode bounds, alias/no-write rejection and
  canonical optional values. Grouping invalid values avoids repeated setup.
- MCP/CLI: 126 passed/five unchanged skips (5.00s).
- Named production spine: 1085 passed/three existing skips (68.60s).
- UI: 138 passed. Ruff check/format pass for 764 files. Routing gates pass.
- Decision-conformance: passing 97,977-ms baseline; 184/184 protected mutations
  killed, zero survived/invalid, source unchanged.
- Broader nine-module diagnostic: 380 passed/one failed/eight existing skips
  (59.71s). Its unchanged fallback-roster fixture also fails on untouched main
  c1c5d9d9 (2.04s). AR-176 owns that sixth stale fixture; do not call it green.
- Metadata, policy, exact worklog, strict docs/tracker and diff checks pass
  before publication. No exhaustive corpus, hosted dispatch, Windows run,
  release artifact, successful installed activation or live staffing claim.

## Follow-ups

Freeze 973acdb9 with the completed builder citations and run all six isolated
criteria through the already usable Codex provider. Only accepted completion
allows a done flip. Publish one PR, merge, then continue to AR-135. Keep the
single failed Codex refresh separate: registration is not trusted activation.
