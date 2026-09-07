---
title: "AR-163 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, security, remediation]
related:
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-163
candidate_commit: fd551fd49bf535c939e66ba5c387fd872621ac67
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-163 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Current eligibility is conjunctive with signature/dependency integrity | 2026-09-07 | agency_runtime/core/roster/sync.py:2832-2904 |
| 1 | test | Rejected and active-basis-drift candidates reopen pending and leave current history | 2026-09-07 | tests/test_roster_remediation.py:1726-1779 |
| 1 | test | Changed active roster invalidates the bound audit without event churn | 2026-09-07 | tests/test_roster_remediation.py:1843-1892 |
| 1 | command-output | Fresh Store and dashboard package passes 167 cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 2 | test | Exact authority row and child dependencies are replayed; pending stays one, history zero, revision unchanged | 2026-09-07 | tests/test_roster_remediation.py:1778-1810 |
| 2 | file | Historical signature and current eligibility are both required by suppression | 2026-09-07 | agency_runtime/core/roster/sync.py:2832-2925 |
| 2 | command-output | Replay case executes successfully in the complete module | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 3 | test | Modified HMAC insert raises SQLite integrity error and rolls back | 2026-09-07 | tests/test_roster_remediation.py:1811-1840 |
| 3 | command-output | Fresh complete remediation module includes the tamper rejection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 4 | file | Approval validates candidate state and current bound audit before marking approved | 2026-09-07 | agency_runtime/core/roster/sync.py:4499-4578 |
| 4 | file | Activation validates approved status, current audit and active basis before applying the delta | 2026-09-07 | agency_runtime/core/roster/sync.py:4788-4858 |
| 4 | file | Current audit check binds candidate identity, policy, roster basis and verdict | 2026-09-07 | agency_runtime/core/roster/review.py:1446-1473 |
| 4 | test | Rejected candidate approval and activation raise, while audit drift also refuses both paths | 2026-09-07 | tests/test_roster_remediation.py:1755-1779 |
| 4 | test | Changed active-basis candidate refuses approval and activation | 2026-09-07 | tests/test_roster_remediation.py:1843-1892 |
| 4 | command-output | Fresh complete tests pass both refusal cases | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 5 | file | Snapshot selects original queued IDs using the absence of current authority | 2026-09-07 | agency_runtime/core/roster/sync.py:2970-3048 |
| 5 | test | Rejected/replayed/tampered state preserves the exact original queue and resolution event counts | 2026-09-07 | tests/test_roster_remediation.py:1811-1840 |
| 5 | test | Roster drift changes only read-time projection, preserving event counts | 2026-09-07 | tests/test_roster_remediation.py:1843-1892 |
| 5 | command-output | Fresh local Store regressions execute without failure | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 6 | file | Current history, all cryptographic history and raw events form nested sets and are differenced into disjoint counts | 2026-09-07 | agency_runtime/core/roster/sync.py:3114-3198 |
| 6 | test | Signed but stale record has counts 0 current, 1 stale, 0 unvalidated and sum 1 | 2026-09-07 | tests/test_roster_remediation.py:1755-1776 |
| 6 | test | Duplicate raw and malformed records remain separate from authoritative history | 2026-09-07 | tests/test_roster_remediation.py:2123-2163 |
| 6 | command-output | Both count-classification cases pass in the complete remediation run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 7 | file | Expanded extent requires both nonempty identical revision and exact event-ID prefix | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1624-1684 |
| 7 | test | Loaded pending extent survives a same-revision exact-prefix refresh | 2026-09-07 | tests/dashboard_ui.test.mjs:7432-7487 |
| 7 | test | Reopening invalidates old paged history even with a still-matching first prefix | 2026-09-07 | tests/dashboard_ui.test.mjs:7489-7577 |
| 7 | command-output | All 188 DOM workflow cases pass, including reopening and overlap suppression | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |
| 8 | file | Separate stale/invalid labels and counts contain no source/signing fields | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1322-1358 |
| 8 | test | Rendered stale signed and unvalidated labels are asserted independently | 2026-09-07 | tests/dashboard_ui.test.mjs:7137-7184 |
| 8 | test | Actual API projection excludes raw private prompt sentinel | 2026-09-07 | tests/test_dashboard_operational.py:305-362 |
| 8 | file | Resolution public mapping has explicit metadata and internal-only authority fields | 2026-09-07 | agency_runtime/core/roster/sync.py:2618-2641 |
| 8 | file | All internal source/authority fields are stripped from public remediation items | 2026-09-07 | agency_runtime/core/roster/sync.py:2828-2830 |
| 8 | file | Renderer selects only explicit pending/history metadata | 2026-09-07 | agency_runtime/dashboard/dashboard-render.js:1244-1310 |
| 8 | command-output | Fresh API and rendered DOM checks pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md#fresh-focused-verification |

## Verification

All eight original criteria await isolated candidate-bound checks. No builder
verdict or completion is recorded.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
