---
title: "Worklog: reconcile counts and verify shipped request identity"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags:
  - backlog
  - verification
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
supersedes: []
superseded_by: null
type: worklog
commit: b9d68e5d872046fcb207f5318d323eb63becb601
short: b9d68e5d
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/683
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
---

# Worklog: reconcile counts and verify shipped request identity

## Purpose

Correct the misleading interpretation of 147 unfinished local records as 147
current tracker bugs. The starting state was 43 actual open tracker issues plus
104 unfinished, pre-tracker local records. The owner requested closure of proved
work and retirement of irrelevant agent-authored proposals, excluding Windows
work reserved for the owner.

## Approach

Treat each record as an unverified claim against current product intent, code,
tests, and accepted successor decisions. AR-149's request-identity fix already
exists in production; add fresh HTTP evidence and a builder acceptance record
without making an unnecessary code change. Keep the issue open until its
candidate-bound isolated verdicts are satisfied.

## Challenges encountered

All 138 dashboard UI tests passed, including listener-retention coverage, but
the exact configured function-coverage gate failed: 91.12 percent against 93.
AR-406 and tracker #682 preserve this distinct current gap. It is neither a
passing coverage result nor proof that the historical listener defect remains.

## Decisions and alternatives

Preserve AR-149's three product criteria. Reconcile only its old mandatory full
warning-strict corpus condition with the existing bounded-delivery policy in
[ADR-0105](../decisions/0105-bound-delivery-to-live-demo-checkpoints.md), and keep
the original text as history. Do not create 104 unnecessary trackers, blindly
implement old designs, or call Windows behavior verified from this Linux host.

## Verification

- Four real HTTP request-identity regressions passed in 1.21 seconds.
- The dashboard and disconnect suites passed: 180 tests in 27.28 seconds.
- Exact UI coverage command: 138 test cases passed; coverage exit 1,
  97.80 percent lines, 88.43 percent branches, 91.12 percent functions.
- Metadata and strict documentation checks passed for 1,097 Markdown files;
  strict tracker parity passed for 397 local roadmap records, with the two
  existing PR-tracked historical exceptions. These are not tracker-open counts.
- No product, test, or installer changes. Prior source-identical installed
  production-spine and smoke evidence is explicitly cited, not relabeled as a
  fresh run. No exhaustive corpus or Windows evaluation was performed.

## Follow-ups

Complete AR-149's isolated acceptance and closure; assess obsolete historical
asset-budget requirements under AR-404; address the meaningful UI coverage gap
under AR-406. Track current open trackers separately from unfinished legacy
records as each disposition is completed.
