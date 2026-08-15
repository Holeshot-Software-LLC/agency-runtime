---
title: "Worklog detail: replace push-triggered CI with a local gate runner"
status: active
category: worklog
created: 2026-08-15
updated: 2026-08-15
tags: [ci, cost, gates, verification, tooling]
related:
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-257-separate-decision-conformance-fixture-launcher.md
  - scripts/run_local_gates.py
supersedes: []
superseded_by: null
type: worklog
commit: 30ab92f918e4de6e4ab20a5fd95ffaf62a1d20ca
short: 30ab92f9
date: 2026-08-15
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: replace push-triggered CI with a local gate runner

## Purpose

Hosted CI minutes ran past the monthly allowance and began costing money. The
cause is structural rather than incidental: this repository is developed
direct-to-main, so **every commit** triggered `ci.yml`, whose quality job takes
7-10 minutes.

Worse, the workflow's `concurrency` group cancels a superseded run — but only
after it has been running. The run for `a63dc28a` billed **10m14s** and was then
cancelled by the next push without ever reporting. A burst of small commits
therefore paid for several runs and learned from one.

## Approach

`push` was removed from `ci.yml`. `pull_request` and `workflow_dispatch` remain,
so the full hosted gate is still one command away.

The dispatch path was checked rather than assumed, because it is now the only
way to reach the Linux gate. Two places decide behaviour by event name: the
change classifier treats any non-`pull_request` event as
`code_required=true`, and the whitespace step's `case` has an explicit
`workflow_dispatch` arm comparing against the empty tree. A manual run therefore
verifies everything. The now-dead `push)` arm was left in place because
`test_release_packaging.py` asserts that script's contents.

`scripts/run_local_gates.py` runs the same quality-job commands in the same
order, stopping at the first failure, and names the two things it cannot cover
instead of implying full parity:

* **Linux-only behaviour.** The hosted job runs ubuntu-24.04.
* **The decision-conformance mutation phase**, which dies in ~120 ms on this
  machine because the sandbox redirects `HOME` away from the user
  site-packages holding pytest (AR-257). The runner substitutes a direct check
  that all 151 mutation `before` snippets still match their source exactly
  once — the thing that actually breaks when a guarded line is edited.

## Challenges encountered

**The first version of the runner was wrong in the most dangerous way: it
failed loudly on correct code.** It copied CI's `--basetemp` flag but pointed it
at a repo-relative path. CI aims that flag at an owner-private directory outside
the checkout and also exports `TMPDIR` there. Pointing it inside the working
tree turned a green 681-pass spine into **205 failures**, concentrated in
`test_security_turn_boundaries`, `test_host_boundary_hardening` and
`test_storage_file_trust` — the path-trust suites. It also errored at *setup*
with `FileNotFoundError`, because pytest does not create the parent directory.
The flag was dropped: pytest's default system-temp basetemp is what an ordinary
green local run already uses.

**CodeQL was nearly weakened by accident.** Cutting its per-push scanning looked
like the same kind of saving, until `test_codeql_preserves_events_and_exposes_
one_stable_result` failed — it pins `push`, `pull_request`, `schedule` and
`workflow_dispatch` deliberately. That is a security contract, so the change was
reverted and CodeQL keeps scanning every push.

**The runner immediately found a real defect in its first complete run**: the
worklog ledger was stale for `548bba3a`. The in-flight hosted run failed on the
same gate minutes later, which is a fair check that the local gate reproduces
CI rather than approximating it.

## Decisions and alternatives

`gh workflow disable` was rejected. It is an invisible repository setting;
editing the trigger keeps the decision in git with its reasoning attached.

Removing `pull_request` was rejected: PRs are rare here, so the trigger costs
nothing unused and preserves a gate if one is opened.

The upstream roster audit moved from a daily to a weekly cron. It watches an
external repository, so no local run substitutes for it, but the upstream roster
does not change daily and ~30 hosted runs a month bought nothing ~4 does not.
Its test was renamed from `nightly` to `scheduled` so the name still describes
the job.

## Verification

- `python scripts/run_local_gates.py` — **all 14 gates green in 14.5 minutes**,
  including the fast production spine, the AR-119 matrix evidence list, the
  documentation ledgers, and the dashboard UI coverage thresholds.
- `python scripts/run_local_gates.py --fast` — 12 gates in 1.3 minutes.
- The last automatic hosted run (`548bba3a`) failed on exactly one step,
  "Verify documentation ledgers", with every earlier step green on Linux — so
  the preceding commits were hosted-validated before push CI was retired.

## Follow-ups

- No automatic gate now runs on push. A `pre-push` hook invoking `--fast` would
  make it unforgettable at the cost of push latency; not added without the
  owner's call. ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md))
- The integration coverage shards and the portability matrix still run only on
  `workflow_dispatch`, unchanged by this commit.
  ([AR-119](../roadmap/issue-AR-119-inference-first-workforce.md))
