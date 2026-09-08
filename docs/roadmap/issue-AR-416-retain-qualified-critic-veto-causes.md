---
title: "AR-416: Retain qualified critic veto causes in bounded receipts"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [headers, critic, diagnostics]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/decisions/0240-project-qualified-critic-veto-causes-with-an-omission-marker.md
  - docs/worklog/2026-09-08-captured-native-critic-veto.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-416
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/787
depends_on: []
blocks: []
---

# AR-416: Retain qualified critic veto causes in bounded receipts

## Problem

A native critic returned valid `wrong-neighbor-selection-documentation-evidence-researcher`.
The critic accepts reason codes up to128characters, but adding `critic_` exceeds
the56character projection limit. The projection silently drops the whole reason,
so both the failure receipt and native header lose the standard veto cause.

## Current state

Phase focused_review. Source fix and captured-response regressions implemented. Two captured native turns reproduced the same packet and
qualified veto; each persisted only `staffing_critic_rejected`. The observer
forwarded request/response bytes unchanged and restored owner configuration
byte-for-byte. The actual packet is preserved under roadmap evidence. No
recruiter, critic, eligibility, acceptance or retry change is proposed.

## Approach

Keep the existing exact projection for codes that fit. For an otherwise valid
oversized code, retain a recognized standard veto-ground prefix only at its
hyphen boundary and add `critic_reason_detail_omitted`. An oversized unknown
code gets the omission marker. Preserve all existing code/count/disclosure
bounds. Never truncate a specialist identity or pretend the qualifier survived.

## Dependencies

AR-414 supplied native reproduction and the failed-header renderer. ADR-0240
records this bounded projection rule; the upstream critic contract is unchanged.

## Acceptance

- [ ] The captured qualified veto retains `critic_wrong_neighbor_selection`
      and an explicit omitted-detail marker through routing and preflight receipts.
- [ ] Invalid codes, ordinary short codes, approval, veto and existing length,
      count and disclosure boundaries retain their behavior.
- [ ] The real failed-header/finalizer path displays the retained cause while
      leaving the replayed failure terminal and unaccepted.
- [ ] Repository, tracker, worklog and scoped verification evidence agree;
      source replay is distinguished from an upgraded installed native run.
