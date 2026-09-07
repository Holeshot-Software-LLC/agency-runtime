---
title: "AR-156 current bounded verification reconciliation"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [verification, workflow, cost, evidence]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/RELEASE_CHECKLIST.md
  - tests/test_run_local_gates.py
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-156 bounded verification evidence

## Current scope and repairs

Baseline main 729e7dc4, merge ledger 38af9f61. The manual-only exhaustive
workflow, exact paired sessions, fail-closed aggregate, private local runner
and opt-in timing profile already exist. Do not restore the old push schedule
or repeat the historical exhaustive benchmark merely to reconcile this record.

New regressions reproduced three failures: local normal/fast execution skipped
missing Node and printed All gates passed, while the documented UI command
differed from local/hosted arguments (three failed, six passed, 0.21s).
The local runner now preflights required Node before executing any gate.
Missing Node returns failure with no false success or downstream cost; listing
remains resource-free. Six new runner tests are in both local/hosted fast
workflow lists, with an exact membership regression.

The release checklist now publishes the unchanged source-only 95/86/93 UI
command. Its command is the third arm of the exact local/hosted/documented
argument test. Stale direct-to-main instructions and push-trigger claims are
reconciled to current AGENTS.md and actual triggers, without changing triggers,
matrix membership, policy or thresholds.

## Asset boundary

The broader workflow check found 387,355 dashboard bytes against the existing
strict 387,072-byte ceiling: one failed, 145 passed, five Windows-named cases
deselected (4.86s). The same asset failure reproduced on untouched main.
AR-139's retired 263,168-byte requirement remains retired; its successor
378 KiB guard remains enforced.

Shortening three full-line comments in dashboard-config.js removes 297 bytes.
After removing full-line comments from both versions, every remaining byte
equals main 729e7dc4. No executable JavaScript, CSS, markup, resource membership
or UI behavior changed. The payload is 387,058 bytes, 14 bytes below the strict
ceiling; this is a narrow margin, not permission to relax the guard.

## Fresh verification

- New runner and local/hosted/documented command checks: nine pass, 0.10s.
- Add exact resource-addressability/budget regression: ten pass, 0.12s.
- Complete fast workflow files: ci_change_scope, ci_sharding, ci_session_pair,
  release_packaging and run_local_gates with `-k 'not windows' -q -W error`:
  165 pass, five Windows-named cases deselected, zero skips/failures, 4.82s.
  These include exact matrix/timeout/event/aggregate contracts and real local
  paired-process timeout/descendant cleanup; not native Windows execution.
- Named 29-module production spine: 1085 pass, three existing skips, 68.41s.
  Python runtime and named spine files remain unchanged after this run.
- Complete source-instrumented UI after comment compaction: 188 pass, zero
  skips/failures, 250.23ms, 96.93/86.71/95.71 above unchanged 95/86/93.
- Ruff check/format pass (766 Python files); fast CLI listing includes all
  required workflow files and performs no execution.

The focused profile/local-loop selection was 17 passed, four failed and 29
deselected (1.62s), not green. Four unmarked tests expect Windows-only `auto`
profile states on Linux: exact_profile_is_deterministic_and_drives_duration_lpt,
missing_invalid_unsupported_and_strict_profile_states_are_bounded,
product_source_drift_uses_compatible_weights_but_strict_mode_rejects and
timing_profile_selection_requires_explicit_auto. Production deliberately returns
unsupported-runtime outside Windows CPython. All four plus the asset failure
reproduced together on untouched main (five failed, 0.68s). No Windows loader
guard or fixture was changed, skipped or represented as passing.

## Hosted and historical limits

Read-only inspection on September 7 reports the CI workflow active. The latest
listed [CI run](https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/33437822949)
was an August 31 pull request, cancelled at c6e9e46c; the preceding two were
failures. This does not establish the current billing cause or a current
candidate's hosted pass. No workflow was dispatched or setting changed.

The actual workflow has no push trigger. PRs use their governed code/docs lane;
manual dispatch alone requests exhaustive coverage/compatibility. Existing
35-/70-minute ceilings already implement ADR-0097's cleanup envelope.
The 74.444-percent local Windows speedup and failed 30-percent timing-profile
promotion threshold in the original record remain historical, not new results.

## Exact packaged browser check

Canonical wheel and source archive built from clean ledger commit
dccb4e8502d8f35de74ed5a68915272df520a32a, following repair 9fb95136.
The wheel SHA-256 is
9f148a13c3528910f5d10b7497ef43ac26a287a7c087488602404ffb63112aa9.
Its fresh private installation supplied every browser-served asset; all ten
hashes match the package. No previous artifact or receipt was overwritten.

The [browser report](AR-156-browser-20260907/report.json), observed at
2026-09-07T07:56:53.222Z, has SHA-256
07513f7f7f22234a3aa61f9e379cd1ef9a362f890433c5b414d36536d66eaccb.
Chromium 152.0.7977.64, Playwright 1.63.0 and axe 4.13.0 exercised seven
loaded views at 1280/1024/375 widths: all 21 pass, no automatic accessibility
violations, horizontal overflow, metric clipping or unexpected errors.
At every width, real polling retained dirty inputs/focus/selection/details,
keyboard scrolling worked, and injected API failure retained the revision,
surfaced correlated stale evidence and recovered. Three overview screenshots
are retained; the narrow screenshot was visually inspected.

Scope is a private authenticated five-agent Store with host inspection stubbed
and all server outbound connections denied. Axe retains incomplete contrast
checks for gradients/pseudo-elements; zero automatic violations is not full
WCAG, screen-reader, native-host or normal-session activation certification.
Pre-demo telemetry reported 77.9 percent remaining at 07:56:42Z.

## Disposition

Retain AR-156 open with all thirteen original criteria unchanged. Bounded local
feedback repairs are verified; native Windows/profile evidence and explicit
hosted topology evidence remain owner-controlled. Full corpus, aggregate
Python coverage and interpreter matrix are optional under ADR-0105, not a
routine completion gate or a reason to retry unattended. Exact rebuilt-wheel
browser evidence passes within the scope above; publish this bounded repair
through one normal PR, then continue at AR-157. Counts remain 40 actual open
trackers plus 91 unfinished legacy records (131 local unfinished).
