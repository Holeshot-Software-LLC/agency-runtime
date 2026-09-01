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

## Reconciliation pass (2026-09-01, owner-authorized)

Applied on this branch and on the live tracker:

- **Labels backfilled** on all ten label-missing trackers (#362 #368
  #372 #373 #386 #387 #398 #399 from the epic front matter; #246
  `epic:operations`; #372's `epic:dashboard` label already existed).
- **AR-220** doc `tracker_url` fixed to #263 (doc already `wont_do`,
  tracker CLOSED NOT_PLANNED — now consistent).
- **AR-180 is an ID collision, not a pairing**: tracker #155 "Bound
  automatic Windows portability fan-out" carried a stale `[AR-180]`
  tag while the roadmap's AR-180 is the codex activation canary; no
  doc covers #155's subject. #155 was retitled to drop the colliding
  tag; the AR-180 doc stays open and untracked (allow-listed).
- **AR-227/AR-228 are PR-tracked** (merged #236/#237, docs done):
  `verify_tracker` now skips items whose `tracker_url` is a pull
  request — `gh issue list` can never match them.
- **Pre-tracker allow-list implemented**:
  `docs/roadmap/pre-tracker-history.txt` (132 IDs), honored by
  `verify_docs --require-tracker` and by `verify_tracker`'s
  `missing_remote` check; both gates fail on stale entries that later
  gain a `tracker_url`. `verify_docs --require-tracker` now **passes**.
- **Six done-doc trackers closed** (initially denied by the automation
  permission classifier, then completed after the owner's direct
  go-ahead): #272 (AR-254), #335 (AR-297), #345 (AR-331), #346
  (AR-332), #347 (AR-333), #349 (AR-334) — each closed as completed
  with an AR-347 reconciliation comment. The
  closure-pending-authorization warnings are gone.
- **Deliberately NOT flipped to done**: AR-115, AR-120, AR-127,
  AR-199, AR-235, AR-237, AR-250, AR-251, AR-261 — their trackers
  were closed COMPLETED, but every doc still has unchecked Acceptance
  boxes and `verify_docs` correctly refuses `done` without them. Each
  needs per-item acceptance verification (or an explicit owner
  decision) before the doc-side flip; this is the remaining
  substantive work, not a mechanical sync.
- Branch skew note: `missing_local=[AR-345, AR-346]` clears once PR
  #401 lands their docs (proven by a local test merge).

## Nine-doc acceptance verification (2026-09-01, owner-authorized)

Verdict per doc, from per-criterion code/tracker audits:

- **AR-237 — COMPLETED.** AR-256's reopen reason ("no PR evidence")
  was factually wrong: merged PR #247 carries the slice. The one real
  gap (plain `hiring show` omitted `work_unit_id`) is fixed with a
  strengthened test; all boxes checked with citations, doc and
  registry now `done`, matching its CLOSED tracker (#246). See the
  doc's completion-verification section.
- **AR-235 — stays open.** The Python hiring path is built (isolated
  security review, bounded repair, inference profiles, amend-first,
  cap softening) but the entire operator/dashboard plane is unbuilt:
  no security-review trail, no same-provider warning surface, no
  hire-count/top-gaps charts, no review-window badge, no workforce
  health summary. Audit also found three fresh defects worth their
  own attention: `enforce_strict_independence` is production-dead
  code (defined and tested, never called — `strict_independence:
  true` silently does nothing); repair-budget exhaustion persists no
  `rejected` hiring-case row (the audit-trail contract has no durable
  record); `classify_contractor_risk` still acts as a binding verdict
  for owner-approval classes, not a hint.
- **AR-115, AR-120, AR-127 — stay open.** Deliberate AR-256 reopens
  with named unmet gates (installed forbidden-specialist matrix;
  nightly ingestion with no successor; no durable full-suite
  receipt). No later evidence satisfies them.
- **AR-199 — stays open.** Its first box (every Codex parent turn
  reports the resident header without Stop correction) is genuinely
  unmet — the AR-344/AR-345/AR-346 fail-open family is this exact
  gate failing.
- **AR-250, AR-251 — stay open.** Remaining scope was deferred with
  no successor issue (upgrade plan/run flow; card modes for roster/
  policy/config).
- **AR-261 — stays open.** The final box requires a later authorized
  exact-main hire draw; no record proves one.

**Disposition applied for the eight still-open docs:** their trackers
(#127, #133, #151, #161, #244, #259, #260, #309) were REOPENED with
citation comments on 2026-09-01 after the owner's direct go-ahead —
AR-256's Limits section had deferred these tracker changes and they
had never happened. With the reopens applied,
`verify_tracker --allow-open-complete` reports a single remaining
error (the AR-345/AR-346 branch skew), and a local test merge with
PR #401 proves the full pass: **"tracker validation passed for 338
roadmap items", exit 0, zero warnings** — the gate's first recorded
fully-green run.

## Acceptance

- [x] `verify_tracker`'s ID matching recognizes the current `AR-NNN:`
      tracker title style alongside `[AR-NNN]` (or all tracker titles
      are normalized to one recognized style), eliminating the
      false-positive `missing_remote` rows for tracked issues.
- [x] The owner disposition for each of the 20 state/label/URL
      mismatches is recorded and applied (docs and trackers agree, or
      the divergence is explicitly annotated). (2026-09-01: labels,
      URLs, the #155 collision, PR-tracked items, six done-doc
      closes, the AR-237 completion, and eight premature-close
      reopens — every mismatch dispositioned.)
- [x] The historical no-tracker items are either backfilled with
      trackers, or the gate gains an explicit, versioned allow-list of
      pre-tracker history so `--require-tracker` is meaningful for new
      work.
- [x] Both strict gates pass on main (or fail only on changes under
      test), restoring them as usable release-validation gates.
      (`verify_docs --require-tracker` passes on this branch;
      `verify_tracker --allow-open-complete` passes for 338 items on
      the local test merge with PR #401 — full green lands when both
      PRs merge.)
