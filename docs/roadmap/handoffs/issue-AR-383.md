---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar373-acceptance
evidence_commit: 1c1bf0797307f628992dfaba5ea977aa4b6e0205
minimum_ledger_commit: 4d0d7c1b66be8d2b847e6b4ce00534ea92a3040e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> The 2026-09-03 stack (PRs #582 to #592, plus the ledger resync #593) is
> merged: `main` at `4d0d7c1b` carries ADR-0198 to ADR-0202 and the done
> AR-384, AR-385 and AR-386. This capsule rides on `claude/ar373-acceptance`
> with the AR-373 record; once that PR merges, read it from `main`.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
merged runtime is installed for claude, and the losses that remain are the
recruiter's judgment and the critic's.

## checkpoint

Of the previous package: AR-386 done (#590), ADR-0202 merged (#591), AR-385
done (#592) after one held freeze and one contradicted verifier pass, the
stack merged in order and the ledger resynced (#593), the merged runtime
installed (venv `4d0d7c1b`, launchers publish `9fb2db79e58d`), the live
store reconciled (generation 307, the API platform card no longer in
`platform`), and the AR-373 acceptance record frozen at `4d0d7c1b` on this
branch.

- **AR-384 option 2** (ADR-0201): `platform-engineering` no longer promotes
  the API platform card into `platform`, so under plan authority `platform`
  is unserved and ADR-0198 waives it; the planner is shown
  `planning_taxonomy.domains_by_artifact_kind` (the verifier's eligibility on
  a probe unit per artifact kind, 13 ms over 291 contracts) and a unit none
  of whose domains is served is rejected as `plan_unit_domains_unserved` for
  planner repair. Weak rule: one served domain suffices. Exempt: a kind with
  nothing proven, compiler-chosen domains, a declared `novel_capability`
  domain.
- **AR-384, AR-385 and AR-386 are done** (PRs #589, #592, #590): records
  frozen at `7c67b524`, `1c1bf079` and `6b79736c`, isolated codex verifier
  satisfied on every criterion. `verify_tracker.py` reports `missing_remote`
  for all three until the owner authorizes their tracker issues.
- **Install**: `claude` complete (`agency install --agent claude`, umask
  077); `codex` partial at `activation_required`, an attended step in a fresh
  Codex terminal TUI then `agency install --agent codex --verify-activation`;
  hermes and openclaw not reinstalled (openclaw's gateway is live and its
  install fails closed). `agency doctor` fails only on the claude harness
  battery, a stale 2026-09-02 record (0 of 2 `canary_failed` on Claude Code
  2.1.258 against a proof on 2.1.257) that predates every change here.
- **ADR-0202 (this branch)**: a candidate row is read as the deployment sends
  it where no safety property lives (missing evidence array is empty, a
  string-keyed object is its keys, identity and score stay mandatory); the
  evidence charset admits `_`; one `units` wrapper is unwrapped; a reply that
  is not a units object is recorded per unit as `missing_work_unit` with
  `recruiter_response_shape_invalid` and repaired; a verifier rejection's
  `unit=code` rows project onto the attempt on both receipts, from the closed
  `STAFFING_VERIFIER_REASON_CODES`, and survive the read-back re-projection.
- An installed store gets the vocabulary fix only through `agency install`'s
  reconciliation (one re-projection of 280); every measurement ran against a
  reconciled **copy**, and the live store was not written.

| eleven install wordings, strict mode, ADR-0202 runtime, store copy | turns |
|---|---|
| completed, critic approved | 4 (204, 206, 207, 209); ADR-0201 run 3, AR-386 run 2 |
| reply shape recorded and repaired (206 not a units object; 304 rows without `score`) | 2, one of them completed |
| transport could not read the reply (`failed`, not rejected) | 1 (201) |
| verifier confidence too low | 1 (202) |
| critic `wrong-neighbor-selection` | 4 (203, 205, 208, 304); 205's team was approved on the ADR-0201 run |
| recruiter gap, hiring ran, no hire | 1 (305) |
| rejected attempts blank on the receipt | 0 with the final code (202's were captured before the re-projection fix; its detail round-trips offline) |

## completed-evidence

**On `main`.** ADR-0202 at `760d631e` and `1c1bf079` (PR #591):
`_normalized_candidate_row`, `_nomination_rows`, the accumulator's recorded
shape and repair-set failures, the `_` charset, two new diagnoses,
`STAFFING_VERIFIER_REASON_CODES`, the verifier rows on both receipts,
`tests/test_recruiter_reply_residue.py` (16 tests), two curated mutations,
`AR-373-AR-385-residue-evidence-20260903.txt`.

**On the stack.** ADR-0201 at `7c67b524` (PR #588) with
`tests/test_planner_domain_service.py` and
`AR-384-option2-evidence-20260903.txt`; the AR-384 and AR-386 flips (PRs
#589, #590). **Capture recipe.** Scratchpad `capture387.py` / `capture388.py`
(capture386 plus a `_PlanPolicyValidationError` hook and
`Store(db_path=<copy>)`), `raw387/`, `raw388/`; store copies
`agency.db.ro-copy` and `agency.db.branch-copy` (reconciled, generation 307);
`PYTHONPATH=<worktree>` with the installed venv python.

**Live facts worth keeping.** The planner has not named `platform` or
`desktop` on a plan unit in 22 turns. The recruiter deployment still omits a
candidate's `score` (304) or returns no JSON object (201); both are recorded,
neither readable. The critic's verdict on an identical team differs between
runs (205). The recruiter ranks modify-authority implementers on plan units,
leaves eligible dual-domain planners unranked, and on 305 declared a gap.

## exact-blocker

Nothing blocks at the contract level: every rejected recruiter attempt is
recorded and the reply shapes the deployment sends are read where they can
be. Two things wait for the owner: the codex attended trust step, and the
tracker issues for AR-384, AR-385 and AR-386. What remains in the runtime is
judgment: four critic wrong-neighbour vetoes of eleven, one recruiter gap
hiring did not fill, one confidence floor, one reply the transport could not
read, and the stale claude battery to re-prove with `agency battery`.

## same-task-continuity

The previous capsules' traps hold. Three more:

1. **A stored contract does not re-project itself.** `_CATEGORY_DOMAINS`
   changes reach a store only through `reconcile_packaged_workforce_contracts`
   (`agency install`); measure on a reconciled copy.
2. **`plan_policy_violations` needs `known_domains`** beside `served_domains`,
   or a declared `novel_capability` unit is bounced back to the planner.
3. **Receipts re-project on read.** A row admitted only from a detail string
   vanishes when the receipt is read back; the list path must admit it too.

## next-bounded-work-package

In this order.

1. **AR-373 flip**: merge this branch's record PR once its verdicts are
   satisfied (the issue records them); tracker #537 closure and the AR-384,
   AR-385, AR-386 tracker issues need the owner's authorization.
2. **Owner steps**: complete codex activation in a fresh Codex terminal
   (`Trust all and continue`, then `agency install --agent codex
   --verify-activation`); re-prove the claude battery with `agency battery`.
3. **Recruiter authority blindness**: it ranks modify-authority implementers
   on plan units and leaves eligible dual-domain planners unranked; a prompt
   or repair-contract change measured on the eleven wordings, with the
   critic's run-to-run variance on an identical team (205) alongside.
4. **Unreadable deployment residue** (omitted `score`, no JSON object):
   operator territory at the LiteLLM alias; recorded, not fixed.
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `1c1bf079` (now on `main`): ruff clean but for one pre-existing RUF024;
`tests/test_recruiter_reply_residue.py` 16 passed; the affected suites 316
passed, 1 skipped; named fast spine 1004 passed, 3 skipped under `-W error`;
decision-conformance 174 of 174 killed, `source_unchanged: true`;
`docs_metadata.py --check`, `verify_docs.py`, `update_worklog.py --check`
green on every branch before merge. Every flip verified `--all` satisfied
(AR-385 on its second pass).

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
