---
title: "AR-431 acceptance verification record"
status: active
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [acceptance, codex, recruitment]
related:
  - docs/roadmap/issue-AR-431-preserve-keep-going-task-context.md
  - docs/worklog/2026-09-10-codex-recruitment-context.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-431
candidate_commit: pending
evidence_cutoff: 2026-09-10
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/839
---

# AR-431 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the keep-going
context loss and one fresh Codex initial/follow-up sequence. The original critic
veto is not assumed erroneous; original raw model packets are unavailable.
The fresh follow-up retained invalid reranking and a primary recruiter timeout;
configured fallback and the independent critic then succeeded. It is not a
zero-failure rate or all-host claim. No failed receipt is reopened. Full native
Store records, card context, collector and run harness are in the candidate.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact failed classification, matching reconstructed state hash, bounded repair then critic veto, and separate transport limit | 2026-09-10 | docs/roadmap/evidence/AR-431-original-summary-20260910.json:1-54 |
| 1 | file | Read-only collection restricts retained runs to the failed turn's temporal predecessor and verifies the exact state revision | 2026-09-10 | docs/roadmap/evidence/AR-431-collect-original-20260910.py.txt:1-18 |
| 1 | command-output | Old classifier fails the keep-going correlation and real-preflight regressions | 2026-09-10 | docs/roadmap/evidence/AR-431-negative-20260910.txt:70-84 |
| 2 | file | Classifier7 extends only the bounded continuation phrase set | 2026-09-10 | agency_runtime/core/turn_intent.py:30-67 |
| 2 | file | Completed tasks require fresh selection, reroute and execution decisions | 2026-09-10 | agency_runtime/core/turn_intent.py:855-879 |
| 2 | test | Failed/untrusted-state and explicit-new-request guards plus real preflight rejection of completed-assignment replay | 2026-09-10 | tests/test_completed_task_followup.py:25-140 |
| 2 | file | Store context is retained only with matching source and revision guard | 2026-09-10 | agency_runtime/core/preflight.py:250-295 |
| 2 | file | Continuation gate preserves source correlation and bounded routing context | 2026-09-10 | agency_runtime/core/preflight.py:1465-1482 |
| 2 | file | Existing independent critic failure returns before accepted staffing | 2026-09-10 | agency_runtime/core/workforce/inference.py:5055-5090 |
| 2 | command-output | Additional focused strict critic tests pass | 2026-09-10 | docs/roadmap/evidence/AR-431-critic-focused-20260910.txt:1-2 |
| 2 | command-output | Classifier and completed-follow-up regression suite passes | 2026-09-10 | docs/roadmap/evidence/AR-431-focused-20260910.txt:1-4 |
| 3 | file | Exact native correlation, recipe22/classifier7, fresh inference and no assignment replay | 2026-09-10 | docs/roadmap/evidence/AR-431-native-summary-20260910.json:1-87 |
| 3 | file | Authoritative follow-up final event and exact five Store-matching header values | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-native-20260910.json:626-659 |
| 3 | file | Complete native card context, segment1 | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-card-context-20260910.txt:1-100 |
| 3 | file | Complete native card context, segment2 | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-card-context-20260910.txt:101-200 |
| 3 | file | Complete native card context, segment3 | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-card-context-20260910.txt:201-300 |
| 3 | file | Complete native card context, segment4 | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-card-context-20260910.txt:301-379 |
| 3 | file | Native request/final provenance and complete inferred/retained card comparison | 2026-09-10 | docs/roadmap/evidence/AR-431-followup-cards-20260910.json:1-71 |
| 3 | command-output | Focused and required fast checks on the exact source, with canonical artifact identity and scope | 2026-09-10 | docs/roadmap/evidence/AR-431-validation-20260910.json:1-92 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
