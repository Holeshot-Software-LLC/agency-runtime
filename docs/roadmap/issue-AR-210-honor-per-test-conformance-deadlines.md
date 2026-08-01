---
title: "AR-210: Honor per-test decision-conformance deadlines"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [testing, mutation-testing, timeout, evidence]
related:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-210
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/205
depends_on: []
blocks: []
---

# AR-210: Honor per-test decision-conformance deadlines

## Problem

`agency eval decision-conformance --timeout 90` documents a per-test deadline,
but the evaluator passed every unique baseline node to one pytest subprocess
under one 90-second aggregate timeout. The baseline grew from nine protected
nodes to 59 and now times out while still green, before any curated mutation
runs. This makes the default release gate reject its own valid test set.

## Current state

The AR-209 exact-head gate stopped after 90.026 seconds with zero of 73
mutations attempted and `source_unchanged: true`. The durable source checkpoint
is intact, and no push, merge, install, or product trial followed the failure.
The bounded candidate now invokes each unique baseline node independently and
stops on its first non-green result. All 12 evaluator tests, Ruff, formatting,
and ordinary validation of 595 Markdown documents pass. Tracker issue
[#205](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/205)
records the same scope. On exact checkpoint `aa26721`, the default command
passed its 59-node baseline in 169.176 seconds, killed all 73 mutations with
zero survivors or invalid results, and left every source input unchanged.

## Approach

1. Run each unique baseline node in the same private copy but in its own pytest
   subprocess under the existing per-test deadline.
2. Stop baseline execution at the first nonzero result or timeout and retain
   the cumulative duration plus exact failure classification.
3. Keep every mutation in its existing fresh private copy and under the same
   unchanged per-test deadline.
4. Prove per-node deadlines and fail-fast behavior with focused unit tests,
   then rerun the default command without a timeout override.

## Dependencies

ADR-0113 owns the isolated green-baseline and curated-mutation evidence
contract. AR-209 is the first exact-head delivery blocked by the aggregate
timeout mismatch.

## Acceptance

- [x] Every unique baseline node receives the configured timeout independently.
- [x] The baseline stops at the first failed or timed-out node and does not run
  any mutation.
- [x] The default command passes the current baseline and kills all 73 curated
  mutations without changing source inputs.
- [ ] Focused tests, the named fast spine, documentation validation, formatting,
  and diff checks pass on the exact source revision.
