---
title: "AR-347: Reconcile the tracker parity backlog so the strict tracker gates can pass"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [documentation, trackers, parity, governance]
related:
  - docs/roadmap/issue-AR-254-reconcile-canonical-worklog-history.md
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-347
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/404
depends_on: []
blocks: []
---

# AR-347: Reconcile the tracker parity backlog so the strict tracker gates can pass

## Problem

The strict tracker gates (`python scripts/verify_docs.py
--require-tracker` and `python scripts/verify_tracker.py`) fail
repo-wide on long-accumulated parity gaps, so they cannot be used as
gates: every run fails on history regardless of the change under test.
AGENTS.md requires both after approved tracker creation, and release
validation "remains strict" — today that requirement is unsatisfiable.

Measured 2026-09-01 on main `a2919e71`:

1. **134 roadmap items with no tracker URL** (`verify_docs
   --require-tracker`): AR-128..AR-177, AR-180..AR-198, AR-225,
   AR-226, AR-252, AR-253, AR-255..AR-258, AR-263, AR-267..AR-288,
   AR-299..AR-330 (contiguous ranges abbreviated; exact list is the
   gate's output).
2. **142 registry IDs reported `missing_remote`** by `verify_tracker`
   — a superset of (1) that also includes **AR-337 through AR-344,
   which do have live trackers** (#362, #372, #373, #386, #387, #398,
   #399 among them). The matcher recognizes only the older bracketed
   title style (`[AR-336] …`); every recently filed tracker uses the
   `AR-NNN: …` style and is invisible to it. Until the matcher accepts
   both styles (or titles are backfilled), even perfectly tracked new
   issues count as parity errors.
3. **20 state/label/URL mismatches**: trackers closed while the doc is
   open — AR-115, AR-120, AR-127, AR-180, AR-199, AR-235, AR-237,
   AR-250, AR-251, AR-261; docs done while the tracker is open —
   AR-254, AR-297, AR-331, AR-332, AR-333, AR-334; `tracker_url` does
   not match the issue URL — AR-180, AR-220; missing epic labels —
   AR-180 (`epic:host-integrations`), AR-237 (`epic:operations`).
   Each state disagreement needs an owner decision (close the tracker,
   reopen the doc, or record wont_do) rather than a mechanical sync.

AR-345 (#402) and AR-346 (#403), filed 2026-09-01 on the PR #401
branch, pass both gates; they are unaffected by this backlog.

## Matcher fix (2026-09-01, this branch)

`verify_tracker.py` now matches both title styles (regression test
pins bracketed, colon, and no-separator titles). Re-measured after the
fix: `missing_remote` drops 142 → exactly the 134 pre-tracker docs;
AR-337..AR-347 get real comparisons, which surfaced that **every
colon-style tracker was filed without its `epic:` label** (AR-337..
AR-344 plus this issue's own trio). The three trackers filed this
session were corrected immediately (#402/#403 `epic:reliability`,
#404 `epic:documentation`); the AR-337..AR-344 label backfill is
mechanical (each doc's `epic:` front matter is authoritative — note
AR-339 needs an `epic:dashboard` label that may not exist yet) and
stays in item 2 below. AR-345/AR-346 read as `missing_local` only
until PR #401 merges their docs.

## Acceptance

- [x] `verify_tracker`'s ID matching recognizes the current `AR-NNN:`
      tracker title style alongside `[AR-NNN]` (or all tracker titles
      are normalized to one recognized style), eliminating the
      false-positive `missing_remote` rows for tracked issues.
- [ ] The owner disposition for each of the 20 state/label/URL
      mismatches is recorded and applied (docs and trackers agree, or
      the divergence is explicitly annotated).
- [ ] The 134 historical no-tracker items are either backfilled with
      trackers, or the gate gains an explicit, versioned allow-list of
      pre-tracker history so `--require-tracker` is meaningful for new
      work.
- [ ] Both strict gates pass on main (or fail only on changes under
      test), restoring them as usable release-validation gates.
