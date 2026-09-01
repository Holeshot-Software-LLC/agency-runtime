---
title: "AR-360: Grade harness batteries with pass@k and pass^k trial semantics"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [battery, reliability, flakiness, grading]
related:
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-360
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/433
depends_on: []
blocks: []
---

# AR-360: Grade harness batteries with pass@k and pass^k trial semantics

## Problem

The harness battery renders a single-shot verdict per host, so a flaky
window (AR-353) produces reds that operators overturn by ad-hoc rerun
("retry until green"), and a genuinely intermittent regression can slip
through on a lucky single pass. Both 2026-09-01 deploys hit this:
hermes failed its first attempt and passed the second, with no recorded
basis for preferring either result.

## Current state

`agency battery` runs each host once; the report has no notion of
trials. Operator lore ("hermes flaps ~50%, retry once") lives in
session memory instead of the product.

## Approach

Adopt the k-trial semantics from eval-driven development (lifted from
ECC's eval-harness skill, owner-approved 2026-09-01):

- Safety-critical checks (wiring trust, hook activation, finalization
  round-trip) grade as **pass^k** — k independent trials, all green.
- Checks overlapping known-flaky windows grade as **pass@k** — pass if
  any of k trials succeeds, with every trial recorded.
- The battery report names the grading mode and records each trial, so
  a flap is data (feeding AR-353 measurement) instead of noise.

Keep k small and configurable (default 2-3); single-trial remains valid
for cheap deterministic probes.

## Dependencies

- Complements AR-352 (per-session delta isolation) — trial recording
  should not double-count foreign-session failures.

## Acceptance

- [ ] Battery checks declare a grading mode; safety-critical checks
      require pass^k and flaky-window checks report pass@k.
- [ ] Every trial outcome is persisted in the battery report.
- [ ] A simulated 50%-flaky check is graded correctly under both modes
      in regression tests.
