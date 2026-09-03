---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar384-coverage-gaps
evidence_commit: 1711bcaa8d507fd7489ea3f454785e51f29c05d7
minimum_ledger_commit: 0530ed961457091c88efc2b799ea7ce50a61ee82
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> **This capsule is not on `main`.** It lives on branch
> `claude/ar384-coverage-gaps`, which stacks on `claude/ar373-recruiter-payload`
> (PR #583) and then `claude/ar370-acceptance` (PR #582). ADR-0198 and the
> AR-383, AR-384, AR-385 and AR-386 documents it cites are on the same stack.
> Merge the open PRs in order or check out `claude/ar384-coverage-gaps` before
> relying on any of them. If you are reading this from `main`, the PRs have
> merged and this note is spent.

Start-here capsule. The staffing investigation has moved one gate: the verifier
no longer kills install turns, the strict critic does.

## checkpoint

Item 1 of the previous package is done. AR-384 is implemented per ADR-0198 on
`claude/ar384-coverage-gaps`: tokens the roster declares but cannot serve for a
unit are waived from team sufficiency and recorded as `roster_coverage_gap`;
tokens nobody declares stay mandatory; the `operations` capability reads the
`operations` domain. Two departures from option 1 as filed are in the ADR: a
blanket waiver broke the regulated-assurance doctrine, and the waiver alone
left the captured helix reply dead on `capability:operations`.

| nine fresh install turns, branch runtime, strict mode | turns |
|---|---|
| verifier accepted the install unit with `roster_coverage_gap`; strict critic vetoed | 4 (203, 204, 205, 209) |
| recruiter reply cut at the 2048-token budget, **AR-385** | 4 first attempts, 2 turns lost |
| evidence charset residue, **AR-373** | 2 turns lost |
| `staff_without_safe_team:domain` on coverable `domain:platform` (AR-384 residue) | 3 turns |
| verifier rejected a staff decision on a waived token | 0 |

The captured helix reply replays offline to an accepted decision with
`operations-manager` selected. Live turn 203 reaches the same verifier decision
and dies at the critic. **AR-386** is filed for the critic; it carries
`tracker_url: null` like AR-384 and AR-385 until the owner authorizes.

## completed-evidence

**On the branch (`1711bcaa8d507fd7489ea3f454785e51f29c05d7`).** `typed_staffing_coverage_gaps` in
`staffing_verifier.py` is the one rule for uncovered, waived and unknown;
`_typed_shortlists`, `build_deterministic_proposal`, `_selection` and
`_validate_nomination_decisions` all read it. The receipt projection carries
`coverage_gaps` per unit. `tests/test_roster_coverage_gap.py` pins the contract
(10 tests). The conformance anchor for `_validate_nomination_decisions` was
refreshed. Acceptance record drafted at `candidate_commit: pending` with
evidence in `docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt`.

**Capture recipe, branch code.** Run the AR-383 `capture.py` with
`PYTHONPATH=<worktree>` and the installed venv python
(`~/.local/share/agency-runtime/venvs/0abe4a77.../bin/python`); the installed
`agency` CLI is `main`, not the branch. Session scratchpad: `capture384.py`,
`capture384b.py`, `replay103.py` (offline replay of a captured reply against
the store snapshot), `timing.py`, `raw/2NN-calls.json`.

**Critic verdicts.** `wrong-neighbor-selection` and `planner-domain-mismatch`
are fair; `selected-team-lacks-live-installation-authority` and
`missing-implementation-lifecycle-assurance` on a plan-only install contradict
the advisory doctrine. Details and codes in AR-386.

## exact-blocker

AR-386 and AR-385 together. Every install turn that reaches the critic is
vetoed, and four of nine first recruiter replies were cut at the hardcoded
2048-token budget. Until both move, no install turn completes and hiring is
never reached. AR-385 is small and independent; AR-386 is a contract change
to the critic document and system prompt.

## same-task-continuity

The six traps from the previous capsule hold. Three more:

1. **The decision-conformance eval fingerprints the tree.** Editing any
   package or test file while it runs yields `source_unchanged: false` and
   `passed: false` even with 168 of 168 killed. Rerun on a quiet tree.
2. **`domain:platform` is a vocabulary collision.** The planner means the
   operating system; the roster's `platform` domain is API platforms and its
   only eligible coverer is `api-platform-engineer`. It is coverable, so it
   stays mandatory and the recruiter is pushed to a wrong neighbour. This is
   AR-384's option 2 and is not fixed.
3. **A unit whose required pick is ineligible is now staffed from its
   acceptable set** once unserved tokens are waived. The strict critic caught
   one such wrong neighbour; balanced and fast modes have no critic.

Store backups: `agency.db.pre-ar384-132820` (this session's scratchpad) plus
the earlier two. Nine more preflight turns persisted; no hire landed
(`agent_workers` 291).

## next-bounded-work-package

In this order.

1. **AR-385**: stage-owned reply budget and a truncation record on the receipt.
   Four of nine first attempts hit the cap this session.
2. **AR-386**: state the advisory doctrine and the waived-gap semantics in the
   critic contract and system prompt; record critic codes on the receipt;
   re-measure the nine wordings. Acceptance is one install turn completing.
3. **AR-384 closure**: second PR freezing `candidate_commit` to `1711bcaa8d507fd7489ea3f454785e51f29c05d7`,
   `scripts/verify_acceptance.py --issue AR-384 --all`, flip to `done`.
   Criterion 2 is evidenced at the verifier; say so if the verifier balks.
4. **AR-373 residue**: admit `_` in nomination evidence, default absent
   evidence arrays on forbidden rows.
5. **AR-384 option 2**: constrain planner domains to what the roster serves,
   starting with the `platform` collision.
6. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then AR-370.

## verification

At `1711bcaa8d507fd7489ea3f454785e51f29c05d7`: ruff check and format clean; `tests/test_roster_coverage_gap.py`
10 passed; affected suites 633 passed, 2 skipped; named fast spine 1004 passed,
3 skipped under `-W error`; `agency eval routing` passed; decision-conformance
168 killed, 0 survived, `source_unchanged: true`; `docs_metadata.py --check`,
`update_worklog.py --check`, `update_policy_availability.py --check`,
`verify_docs.py`, `git diff --check` all green. `verify_tracker.py` reports
`missing_remote=['AR-384', 'AR-385', 'AR-386']` by design.

## constraints

- `agency-hiring-critic.timeout_ms` is still **120000**, unevaluated.
- `agency.yaml` is operator configuration; recruiter deployment order and
  `workforce.mode: strict` are the owner's call, not branch changes.
- `max_hires_per_day` is the default 3.
- Never commit to `main`; branch in a worktree, PR, merge with `--merge`.
  Ledger dance on every substantive commit. Tracker writes need authorization.
