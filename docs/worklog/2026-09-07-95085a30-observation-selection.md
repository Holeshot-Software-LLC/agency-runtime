---
title: "Verify current multi-surface observation selection"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [observability, tests, backlog, verification]
related:
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/roadmap/acceptance/evidence/AR-158-observation-selection-20260907.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 95085a3008389fadf8c4c99123cf3eacfc8e1925
short: 95085a30
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/710
related_issues:
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
---

# Worklog detail: Observation selection

## Approach and decisions

Keep the existing exact MCP/HTTP selectors. The old hook observation test was
removed with obsolete child denial in 20f006b6; restore its evidence assertion
on the current three-host R8 prompt-failure case instead. Capture the actual
observation logger directly with automatic restoration, inject unrelated Store
evidence first, and check every envelope for private content. No runtime change.

Store busy matching now requires an explicit request ID; slow/busy cases inject
matching unrelated events and check all envelopes. Nested ordering is evaluated
only after exact-ID filtering. Only the seventh full-corpus gate is explicitly
reconciled under ADR-0105, preserving its wording and the other six criteria.

## Verification and challenges

Focused 13 pass (1.22s); five interface cases pass ten consecutive fresh-process
runs, 50 total at 0.63–0.65s per run. Complete hook-logging/host-hooks/MCP/runtime/
Store observation package passes 135 with five existing skips (36.16s).
Ruff check/format pass, 766 files. No failures or new suppression. Exact-byte
reuse binds the unchanged named spine (1085/three skips), UI 188/current floors
and 21-case wheel receipt. Native Windows/host activation and exhaustive gates
are not claimed. The opt-in sink's parent propagation setting is not changed
in production; the test-only direct logger capture avoids ambient root dependence.

## Follow-ups

Freeze seven builder rowsets at 95085a30 and require isolated acceptance before
closure. Current count stays 40 actual open trackers plus 90 unfinished legacy
records. Publish one normal PR, then continue at AR-159 without changing branch
or account settings absent explicit authority.

## First isolated review

809354be preserves six satisfied criteria and an absent seventh: the reused
spine receipt named the result but omitted command/warning arguments from its
citations. Repair only that rowset by citing the frozen command definition
explicitly. Candidate 95085a30 and the six accepted rowsets remain unchanged;
do not re-run accepted checks or treat a citation gap as a production defect.

## Accepted completion

b0d9efe8 adds the frozen AGENTS command and local constructor citations only to
criterion 7. Its sole recheck satisfies at unchanged 95085a30; the six earlier
accepted checks retain their original IDs and digests. 3da9cfd0 records accepted
completion, with all seven criteria satisfied and original first six unchanged.
Current counts: 40 actual open trackers plus 89 unfinished legacy records,
129 total. Strict docs/tracker, metadata and policy checks pass. Publish normally
before starting AR-159; no new installation, corpus or native Windows claim.
PR #710 carries accepted completion. Fresh enumeration confirms 129 unfinished
records (89 legacy, 40 mapped); end telemetry is 8.7 percent with a clean pair.

## Publication

PR #710 merged normally at 2026-09-07T08:41:00Z as b2ea5946, with reviewed head
699db08da4a1e56d5c324103860223af25142bee. Main was fast-forwarded cleanly to
that merge before the separate AR-159 worktree was created. No hosted check
success is inferred from the empty PR check rollup.
