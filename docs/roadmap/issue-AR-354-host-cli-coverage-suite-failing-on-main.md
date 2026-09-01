---
title: "AR-354: Four host-CLI coverage tests fail on main outside the fast spine"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [testing, reliability, coverage]
related:
  - docs/roadmap/issue-AR-346-hermes-fail-open-draft-replacement.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-354
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/420
depends_on: []
blocks: []
---

# AR-354: Four host-CLI coverage tests fail on main outside the fast spine

## Problem

Four tests in `tests/test_coverage_final_host_cli.py` fail on main
`7197ae11` (verified on a clean checkout, independent of the AR-346
change that surfaced them):

- `test_hook_stdio_constructs_explicit_store` — the hook stdio run
  emits `agency hook codex: TypeError; response publication blocked`
  and constructs no store (`created == []`).
- `test_install_preflight_human_error_and_per_host_exception`
- `test_openclaw_finish_commit_and_outbound_state_fail_closed`
- `test_openclaw_persistence_runtime_disabled_and_constructor_matrix`

The file is not in the AGENTS.md fast Python production spine, and
hosted CI is disabled repo-wide, so recent PRs never executed it; the
regression window is unbounded until bisected.

## Current state

Failure signature captured 2026-09-01; not yet bisected. The
`TypeError; response publication blocked` line also suggests the hook
stdio boundary blocks publication on an internal error — worth
checking against the Rule 8 posture while fixing.

## Approach

Bisect the first failing commit (the file last passed in some earlier
window), fix the tests or the regression they caught, and decide
whether this file (or a representative slice) belongs in the fast
spine so silent breakage cannot recur.

## Dependencies

None.

## Acceptance

- [ ] The four tests pass on main, with the underlying regression (or
      stale fixtures) identified in the fix commit.
- [ ] A decision is recorded on including the file in the named fast
      spine.
