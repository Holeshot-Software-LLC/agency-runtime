---
title: "AR-416: Retain qualified critic veto causes in bounded receipts"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [headers, critic, diagnostics]
related:
  - docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md
  - docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md
  - docs/worklog/2026-09-08-installed-qualified-veto-verification.md
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
The critic accepts reason codes up to 128 characters, but adding `critic_` exceeds
the 56-character projection limit. The projection silently drops the whole reason,
so both the failure receipt and native header lose the standard veto cause.

## Current state

Latest checkpoint: verified 8629e2ed wheel installed, all614package files match,
and captured-verdict replay preserves the cause and terminal rejection. Codex
plugin0.1.0+codex.823aab6fbe85 is registered/enabled; fresh native trust inspection
reports8modified/0trusted. Native verification is waiting_for_operator for /hooks
review in a fresh TUI. No bypass or native attempt; isolated acceptance pending.


Installed-verification package started from b0dfd631. Preliminary canonical
artifacts pass integrity checks, but an extracted regression exposed AR-417.
Its test-only refinement is verified locally; rebuild precedes live install.

Phase fast_verification complete. Source fix and captured-response regressions
pass in PR788; isolated acceptance verdicts remain pending. Two captured native turns reproduced the same packet and
qualified veto; each persisted only `staffing_critic_rejected`. The observer
forwarded request/response bytes unchanged and restored owner configuration
byte-for-byte. The actual packet is preserved under roadmap evidence. No
recruiter, critic, eligibility, acceptance or retry change is proposed.

Current checks: focused 124 passed; production spine 1151 passed/3 skipped;
UI 224 passed; conformance 188/188 killed, source_unchanged=true; docs, Ruff,
routing and strict tracker parity passed. Installed runtime unchanged.

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
