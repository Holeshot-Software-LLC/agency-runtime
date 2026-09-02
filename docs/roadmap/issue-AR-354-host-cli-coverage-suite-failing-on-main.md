---
title: "AR-354: Four host-CLI coverage tests fail on main outside the fast spine"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-02
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

## Implementation (2026-09-02)

Every failure was fixture drift behind a product change that the file never
ran against, plus one product gap the drift was hiding:

- `test_hook_stdio_constructs_explicit_store` — `bc6589b0` added
  `require_existing_current` to the production `Store(...)` call; the
  two-parameter fixture raised `TypeError` inside the boundary, which the
  Stop path swallowed into "response publication blocked" with no store
  constructed. Fixture accepts the keyword and now asserts an empty stderr
  so the next signature drift fails on its cause.
- `test_install_preflight_human_error_and_per_host_exception` — `f5ca1729`
  made `agency install` run every applicable component (the starter-roster
  seed now runs before the dashboard preflight), so a bare `object()` store
  crashed the seed. The stub answers the one seed call; the live-drift
  projection is stubbed so the test stays hermetic.
- `test_openclaw_finish_commit_and_outbound_state_fail_closed` — `3ec69c7f`
  replaced `_finish_exhausted_retry` with `_finish_policy_rejection` and
  `e80cb40c` made `_commit_terminal_outcome` answer with a state string;
  the test now pins that an `unavailable`/`conflict` binding is reported as
  `verification_failed` (not as an evaluated rejection) and a committed one
  as `response_invalid`.
- `test_openclaw_persistence_runtime_disabled_and_constructor_matrix` —
  `3ec69c7f` removed `_persist_continuation_decision` with the
  continuation-claim protocol and turned the verification-failure envelope
  into a non-corrective terminal; the surviving disabled-runtime and
  constructor matrix is what the test keeps.
- `tests/test_owned_adapter_surface_coverage_final.py::test_openclaw_outbound_rejection_preverify_and_native_child_matrix`
  — `f5b60fde`/`d04d1d6b` read a started receipt back after recording it
  and answer with what was recorded; the fixture now serves that read.
- `tests/test_resident_manager_lifecycle.py` (ten failures, found while
  running the wider corpus): the fixture prompt `ping` now classifies as
  substantive and, offline, fails open — which exposed a real product gap,
  fixed as AR-367 (fail-open turns never claimed or acknowledged their
  resident binding). Three tests cleared with that fix alone; the rest were
  re-derived to current contracts: trivial prompts (`ok`) for the ready
  lifecycle, an explicit external-user origin receipt for the two direct
  `run_preflight` replay tests (a direct call without one is rerouted as
  untrusted and forced substantive), the evaluated-rejection shape
  `continue: false` / `AGENCY RESPONSE INVALID` for a header-less draft on
  a ready turn, and Rule 8 (AR-366) for an acknowledgement failure: the
  turn publishes and closes `verification_failed` instead of failing
  closed (test renamed to say so).
- Rule-8 note on the hook stdio boundary: the broad `except Exception` in
  `run_hook_stdio` routes every internal error through
  `_boundary_failure_result`; for non-Stop events that is a documented
  pass-through, and on Stop the AR-366 gates publish Agency-side failures,
  so the swallowed `TypeError` above cost diagnosability, not a turn.

Spine decision: both `tests/test_coverage_final_host_cli.py` and
`tests/test_resident_manager_lifecycle.py` join the named fast Python
production spine (each runs in under 25 s and is deterministic); the file
tuple in `scripts/run_local_gates.py` is the single source and AGENTS.md
mirrors it.

## Dependencies

None.

## Acceptance

- [x] The four tests pass on main, with the underlying regression (or
      stale fixtures) identified in the fix commit — the drifts above,
      each pinned to the commit that introduced it, and the repaired
      fixtures now in the tree.
- [x] A decision is recorded on including the file in the named fast
      spine — both suites added to `PRODUCTION_SPINE`
      (`scripts/run_local_gates.py`) and the AGENTS.md validation block.
