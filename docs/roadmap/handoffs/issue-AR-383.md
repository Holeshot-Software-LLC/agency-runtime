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
branch: claude/ar373-residue
evidence_commit: 7c67b524bcbad9a00bcf269d6fbbe20c27810879
minimum_ledger_commit: 04a0b96b3fa98cbb6d0a90a9c9b8c1a1d7d8d66e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> **This capsule is not on `main`.** It lives on branch `claude/ar373-residue`,
> the top of a stack: `claude/ar386-flip` (PR #590) on `claude/ar384-flip`
> (PR #589) on `claude/ar384-planner-domains` (PR #588) on
> `claude/ar384-closure` (PR #587) on `claude/ar386-critic-contract` (PR #586) on
> `claude/ar385-reply-budget` (PR #585) on `claude/ar384-coverage-gaps` (PR
> #584) on `claude/ar373-recruiter-payload` (PR #583) on
> `claude/ar370-acceptance` (PR #582). ADR-0198 to ADR-0201 and the AR-384,
> AR-385 and AR-386 documents are on the same stack. Merge the open PRs in
> order with `--merge`, or check out this branch before relying on any of
> them. If you are reading this from `main`, the PRs have merged and this
> note is spent.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, and the losses that remain are the
recruiter's judgment and the critic's.

## checkpoint

Of the previous package: AR-386 is done (PR #590); the AR-373 residue is
fixed on this branch (ADR-0202); AR-385 is re-cited and pending its freeze
at this branch's implementation commit, because its third criterion was
contradicted live until ADR-0202.

- **AR-384 option 2** (ADR-0201): `platform-engineering` no longer promotes
  the API platform card into `platform`, so under plan authority `platform`
  is unserved and ADR-0198 waives it; the planner is shown
  `planning_taxonomy.domains_by_artifact_kind` (the verifier's eligibility on
  a probe unit per artifact kind, 13 ms over 291 contracts) and a unit none
  of whose domains is served is rejected as `plan_unit_domains_unserved` for
  planner repair. Weak rule: one served domain suffices. Exempt: a kind with
  nothing proven, compiler-chosen domains, a declared `novel_capability`
  domain.
- **AR-384 and AR-386 are done** (PRs #589, #590): records frozen at
  `7c67b524` and `6b79736c`, isolated codex verifier satisfied on every
  criterion. `verify_tracker.py` still reports `missing_remote` for AR-384,
  AR-385 and AR-386 by design.
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

**On this branch, uncommitted at the time of writing.** `inference.py`
(`_normalized_candidate_row`, `_nomination_rows`, the accumulator's recorded
shape failure, the `_` charset, the new diagnosis), `receipt_projection.py`
(verifier rows, `_nomination_failure_row`), `staffing_verifier.py`
(`STAFFING_VERIFIER_REASON_CODES`), `preflight_failure.py` allowlist,
`tests/test_recruiter_reply_residue.py` (15 tests), one curated mutation and
one refreshed anchor, ADR-0202, the AR-373 and AR-385 issues, the re-cited
pending AR-385 record, `AR-373-AR-385-residue-evidence-20260903.txt`.

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

Nothing blocks at the contract level any more: every rejected recruiter
attempt is recorded, and the reply shapes the deployment sends are read where
they can be. What remains is judgment: four critic wrong-neighbour vetoes of
eleven, one recruiter gap hiring did not fill, one confidence floor, and one
reply the transport could not read. AR-385's flip waits only for its freeze
at this branch's implementation commit and the verifier run.

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

1. **AR-385 freeze and flip**: on a branch stacked on this one, set
   `candidate_commit` to this branch's implementation commit, run
   `scripts/verify_acceptance.py --issue AR-385 --all --provider codex`, flip
   to `done`. Then merge the stack #582 to the top in order with `--merge`
   and run `agency install` under `umask 077` so the store re-projects the
   API platform card.
2. **AR-373 closure**: its four criteria are checked; write its acceptance
   record (none exists), freeze, verify, flip; tracker #537 closure needs
   authorization.
3. **Recruiter authority blindness**: it ranks modify-authority implementers
   on plan units and leaves eligible dual-domain planners unranked; a prompt
   or repair-contract change measured on the eleven wordings, with the
   critic's run-to-run variance on an identical team (205) alongside.
4. **Unreadable deployment residue** (omitted `score`, no JSON object):
   operator territory at the LiteLLM alias; recorded, not fixed.
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

On the working tree before commit: ruff clean on every changed file (one
pre-existing RUF024 on main); `tests/test_recruiter_reply_residue.py` 15
passed; the receipt, inference, truncation, bounds and conformance suites 258
passed, 1 skipped; named fast spine 1004 passed, 3 skipped under `-W error`;
decision-conformance rerun on the final tree recorded in the ledger row;
`docs_metadata.py --check`, `verify_docs.py` green with the pending AR-385
record. The AR-384 and AR-386 flips each verified `--all` satisfied.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
