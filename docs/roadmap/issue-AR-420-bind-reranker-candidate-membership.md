---
title: "AR-420: Bind reranker responses to per-unit candidate membership"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [staffing, reranker, reliability]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-08-reranker-membership-repair.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-420
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/802
depends_on: []
blocks: []
---

# AR-420: Bind reranker responses to per-unit candidate membership

## Problem

Ordinary staffing remains intermittent after the scoped AR-414/415 repairs.
A captured structured reranker response moved candidate IDs between work units;
the broad static schema admitted this output and the exact-membership validator
correctly rejected it. That optional call consumed 25.561 seconds and contributed
no recall evidence. This is one demonstrated defect, not the established cause
of every recruiter abstention or critic veto.

## Current state

Phase live_demo. Main baseline b69c4926 was clean and synchronized. Current
native trace 01a0830f-8143-7542-ac77-5ace98ceb5d4 failed with a subject rejection,
a reranker rejection and critic_wrong_neighbor_selection. Its proposal was not
persisted; the veto remains unadjudicated. The earlier long-task receipt
01a082bc-e1d2-7ec0-a7c2-fb1a675bd220 separately preserves planner/recruiter
shape and capability-coverage failures; no transport recurrence is assumed.

One standalone capture accepted staffing in 71.781 seconds despite the rejected
optional reranker. Its exact reranker request replayed once with per-unit enums
and exact counts passes the unchanged validator in 15.280 seconds. Model,
prompt, credentials and configuration were unchanged. Evidence is
[evidence/AR-420-reranker-membership-20260908.json](evidence/AR-420-reranker-membership-20260908.json).
Focused164 and production1151/three skips pass; UI224 passes. The integration
regression fails on original source. Canonical artifacts verified; installed
source3fe3d7ba matches all614wheel files. Fresh native Codex trace01a0831f-1a40-7a12-a079-3386a3b439d3 has every staffing
stage applied, full card injection, truthful headers and exact accepted final
response hash in41.514s. Isolated acceptance remains pending; PR803 carries
the repair and evidence/AR-420-native-codex-20260908.json.

## Approach

Generate a bounded response schema from the existing offered sets: each unit
variant has its exact identity, candidate enum and candidate count. Inference
retains every permutation. Preserve the downstream validator, one-call recall
budget, typed-only fallback, native reranker transport, recruiter and independent
critic. No manually selected team, retry increase or acceptance bypass.

## Dependencies

ADR-0118 keeps staffing inference-owned. ADR-0171 defines the separate structured
and native reranker transports. AR-404 retains remaining host gates and the
broader unresolved reliability work.

## Acceptance

- [ ] The original response/schema defect is reproduced and the real structured
      transport receives per-unit candidate enums and exact counts.
- [ ] Candidate permutations remain inference-owned, while missing, duplicate,
      invented and cross-unit IDs and malformed units remain rejected; native
      transport, bounded recall fallback, recruiter and critic are unchanged.
- [ ] Bounded real-provider replay and fresh installed evidence agree with
      focused/production checks and exact repository, tracker and worklog records.
