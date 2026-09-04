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
branch: claude/ar387-recruiter-eligibility
evidence_commit: 1c1bf0797307f628992dfaba5ea977aa4b6e0205
minimum_ledger_commit: 736ffcfe33129aa081b30aadc918cde31dace633
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> The 2026-09-03 stack (PRs #582 to #594) is merged: `main` at `736ffcfe`
> carries ADR-0198 to ADR-0202 and the done AR-373, AR-384, AR-385 and
> AR-386. This capsule rides on `claude/ar387-recruiter-eligibility` with
> AR-387 and ADR-0203; once that PR merges, read it from `main`.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
recruiter now sees the eligibility boundary it is held to, the merged runtime
is installed and verified for claude and codex, and the losses that remain
are the critic's judgment and replies the transport cannot read.

## checkpoint

Of the previous package: AR-373 done (#594); codex activation verified
after the owner's attended trust step (`runtime_verified`); item 3, the
recruiter's authority blindness, is filed as **AR-387** and implemented on
this branch under **ADR-0203**: every recall row carries
`eligible_candidate_ids` (the verifier's eligibility over the detail cards,
complete and identity-sorted) and `eligible_candidates_without_card`, the
safe-team repair contract carries `eligible_coverers_by_requirement`, and
both prompts say a card outside the list can be forbidden or omitted but
never staffed. The acceptance record is a pending draft.

- **AR-384 option 2** (ADR-0201): `platform-engineering` no longer promotes
  the API platform card into `platform`, so under plan authority `platform`
  is unserved and ADR-0198 waives it; the planner is shown
  `planning_taxonomy.domains_by_artifact_kind` (the verifier's eligibility on
  a probe unit per artifact kind, 13 ms over 291 contracts) and a unit none
  of whose domains is served is rejected as `plan_unit_domains_unserved` for
  planner repair. Weak rule: one served domain suffices. Exempt: a kind with
  nothing proven, compiler-chosen domains, a declared `novel_capability`
  domain.
- **AR-373, AR-384, AR-385 and AR-386 are done** (PRs #594, #589, #592,
  #590); `verify_tracker.py` reports `missing_remote` for AR-384 to AR-387
  until the owner authorizes their tracker issues, and #537 still needs its
  closure.
- **Install**: claude complete and codex `runtime_verified` on venv
  `4d0d7c1b`; hermes and openclaw not reinstalled (openclaw's live gateway
  fails its install closed). `agency doctor` fails only on the claude battery,
  a stale 2026-09-02 record that predates every change here.
- **Critic variance**: the turn-205 team replayed six times per prompt with
  the cache bypassed: 6 of 6 approved on one prompt, 1 of 6 on the other.
- **ADR-0202 (this branch)**: a candidate row is read as the deployment sends
  it where no safety property lives (missing evidence array is empty, a
  string-keyed object is its keys, identity and score stay mandatory); the
  evidence charset admits `_`; one `units` wrapper is unwrapped; a reply that
  is not a units object is recorded per unit as `missing_work_unit` with
  `recruiter_response_shape_invalid` and repaired; a verifier rejection's
  `unit=code` rows project onto the attempt on both receipts, from the closed
  `STAFFING_VERIFIER_REASON_CODES`, and survive the read-back re-projection.
- Every measurement ran against a reconciled **copy** of the store; the live
  store was reconciled by the install, not by a measurement.

| eleven install wordings, strict mode, ADR-0203 runtime, store copy | turns |
|---|---|
| completed, critic approved | 5 (201, 204, 206, 207, 304); ADR-0202 run 4, ADR-0201 run 3, AR-386 run 2 |
| plan-authority units answered; ranked cards outside `eligible_candidate_ids` | 8; **0** |
| `staff_without_safe_team`, any unit | **0** (AR-386 run 5, ADR-0201 run 2) |
| critic `wrong-neighbor-selection` | 3 (203, 205, 208) |
| replies the transport could not read (no JSON object) | 2 (209 repair, 305) |
| reply shapes recorded and repaired (row shape, not a units object, `invalid_decision`) | 3 |

## completed-evidence

**On this branch, uncommitted at the time of writing.** ADR-0203:
`_annotate_eligible_candidates`, `_eligible_coverers_by_requirement`, the
repair contract field, the prompt sentences, `allowed_candidate_ids`
threaded to the repair contract, `tests/test_recruiter_eligibility_view.py`
(4 tests), one curated mutation and one refreshed anchor, the AR-387 issue
and pending record, `AR-387-evidence-20260903.txt`. **On `main`.** ADR-0202
at `760d631e` and `1c1bf079` (PR #591) with
`tests/test_recruiter_reply_residue.py` (16 tests) and the AR-373 record
(#594).

**On the stack.** ADR-0201 at `7c67b524` (PR #588) with
`tests/test_planner_domain_service.py` and
`AR-384-option2-evidence-20260903.txt`; the AR-384 and AR-386 flips (PRs
#589, #590). **Capture recipe.** Scratchpad `capture387.py` to `capture389.py`
(capture386 plus a `_PlanPolicyValidationError` hook and
`Store(db_path=<copy>)`), `raw387/` to `raw389/`; `critic_replay.py`
(patches `_http_payload` with `cache: {"no-cache": true}`); store copy
`agency.db.branch-copy` (reconciled, generation 307); `PYTHONPATH=<worktree>`
with the installed venv python.

**Live facts worth keeping.** The planner has not named `platform` or
`desktop` on a plan unit in 33 turns; with the eligibility view the recruiter
ranked only eligible cards on every plan unit. The deployment still returns
replies the transport cannot read (209, 305), omits `score`, and once sent a
`decision` outside staff/gap (304, recorded and repaired).

## exact-blocker

Nothing blocks at the contract level. Waiting for the owner: tracker issues
for AR-384 to AR-387 and closure of #537; the stale claude battery re-prove.
What remains in the runtime is judgment and the deployment: three critic
wrong-neighbour vetoes of eleven and two replies the transport could not
read. AR-387's flip waits only for its freeze and verifier run.

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

1. **AR-387 freeze and flip**: merge this PR, then set the record's
   `candidate_commit` to its implementation commit, run
   `scripts/verify_acceptance.py --issue AR-387 --all --provider codex`,
   flip to `done`; reinstall (`agency install --agent claude` and `codex`
   from a venv built at the merged commit) so the prompts reach the hooks.
2. **Owner steps**: tracker issues for AR-384 to AR-387 and closure of
   #537; re-prove the claude battery with `agency battery`.
3. **Critic wrong-neighbour judgment on install teams** (203, 205, 208): the
   critic's contract could carry the eligibility view too, so it does not
   veto the only eligible planners as wrong neighbours; measure on the
   eleven wordings with the cache-bypassing replay.
4. **Unreadable deployment residue** (no JSON object, omitted `score`,
   `decision` outside staff/gap): operator territory at the LiteLLM alias;
   recorded, not fixed.
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

On the working tree before commit: ruff clean but for one pre-existing
RUF024; `tests/test_recruiter_eligibility_view.py` 4 passed; the affected
suites 346 passed, 2 skipped; named fast spine 1004 passed, 3 skipped under
`-W error`; decision-conformance rerun recorded in the ledger row;
`docs_metadata.py --check` and `verify_docs.py` green but for the
steady-state ledger rows this branch's ledger commit indexes. Every flip so
far verified `--all` satisfied.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
