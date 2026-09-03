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
branch: claude/ar384-planner-domains
evidence_commit: 6b79736c0116331094630f7f252fa68992a1fb8d
minimum_ledger_commit: 8fde90dfcf746eb84abe288d7272c3db3441d2dd
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> **This capsule is not on `main`.** It lives on branch
> `claude/ar384-planner-domains`, the top of a stack: `claude/ar384-closure`
> (PR #587) on `claude/ar386-critic-contract` (PR #586) on
> `claude/ar385-reply-budget` (PR #585) on `claude/ar384-coverage-gaps` (PR
> #584) on `claude/ar373-recruiter-payload` (PR #583) on
> `claude/ar370-acceptance` (PR #582). ADR-0198 to ADR-0201 and the AR-384,
> AR-385 and AR-386 documents are on the same stack. Merge the open PRs in
> order with `--merge`, or check out this branch before relying on any of
> them. If you are reading this from `main`, the PRs have merged and this
> note is spent.

Start-here capsule. The platform collision is closed at the planner; what
remains on the install path is recruiter-side residue.

## checkpoint

Items 1 and 3 of the previous package are done on this branch; item 2
(AR-373 residue) is untouched and now the largest loss.

- **AR-384 option 2** (ADR-0201): `platform-engineering` no longer promotes
  the API platform card into `platform`, so under plan authority `platform`
  is unserved and ADR-0198 waives it; the planner is shown
  `planning_taxonomy.domains_by_artifact_kind` (the verifier's eligibility on
  a probe unit per artifact kind, 13 ms over 291 contracts) and a unit none
  of whose domains is served is rejected as `plan_unit_domains_unserved` for
  planner repair. Weak rule: one served domain suffices. Exempt: a kind with
  nothing proven, compiler-chosen domains, a declared `novel_capability`
  domain.
- **AR-384 criterion 2** reworded to the unit shape (plan authority,
  `operations` among its domains, any unit id); **criterion 4** added for
  option 2 and evidenced live. The acceptance record is a pending draft
  again with re-cited rows; freezing and `verify_acceptance.py --all` are
  the next PR.
- An installed store gets the vocabulary fix only through `agency install`'s
  packaged-contract reconciliation (one re-projection of 280). The live
  measurement ran against a reconciled **copy** of the store; the live store
  was not written.

| eleven install wordings, strict mode, ADR-0201 runtime, store copy | turns |
|---|---|
| completed, critic approved, `operations-manager` on every install plan | 3 (205, 206, 305) |
| recruiter contract residue (AR-373 shapes, `{}` repair reply, malformed 941-token reply) | 4 (202, 203, 204, 304) |
| coverable token left unranked (`domain:software-engineering` 201, `capability:risk-analysis` 204) | 2 |
| verifier confidence or margin too low | 1 (207) |
| critic `wrong-neighbor-selection`, not on a platform selection | 2 (208, 209) |
| `staff_without_safe_team` on `domain:platform`; `api-platform-engineer` anywhere; first plan naming `platform`/`desktop` on a plan unit | **0, 0, 0** (were 3, 2, 6) |

## completed-evidence

**On this branch, uncommitted at the time of writing.** `contract.py`
(`_CATEGORY_DOMAINS`), `intent.py` (`served_domains_by_artifact_kind`,
taxonomy field, prompt paragraph), `plan_policy.py`
(`_unserved_domain_violations`, guidance), `inference.py` wiring,
`tests/test_planner_domain_service.py` (13 tests), the recruiter-index pin
(266_264 to 266_253), one curated conformance mutation, ADR-0201, the issue,
the pending acceptance record, CHANGELOG, the inference-stages reference and
`docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt`.

**Capture recipe.** Session scratchpad `capture387.py` (capture386 plus a
`_PlanPolicyValidationError` hook and `Store(db_path=<copy>)`), `raw387/`,
`capture387_results.jsonl`, `capture387.log`; store copies
`agency.db.ro-copy` (pristine) and `agency.db.branch-copy` (reconciled,
generation 307). Runtime: `PYTHONPATH=<worktree>` with the installed venv
python (`~/.local/share/agency-runtime/venvs/0abe4a77.../bin/python`).

**Live facts worth keeping.** The planner, shown the served view, stopped
naming `platform` and `desktop` on plan units without a single live
`plan_unit_domains_unserved`; it now sometimes pairs `software-engineering`
with `operations` (201), which is staffable but forces a two-domain team the
recruiter did not rank. 304's malformed recruiter reply is the AR-385 one
token for token and carried no gateway cache key: the deployment reproduces
it. 209 completed under AR-386 and is vetoed here because the recruiter put
`desktop-app-engineer` on an `[operations]` environment check.

## exact-blocker

Nothing blocks the planner side. The install path now loses turns only at
the recruiter: AR-373's row-shape and evidence residue plus two structural
reply errors (four of eleven), coverable tokens the recruiter leaves unranked
while ranking ineligible implementers (two), scores under the confidence
floor (one), and two semantic wrong-neighbour vetoes. AR-384's done flip
needs the freeze-and-verify PR on this branch's code; a strict turn that
needs both a planner repair and a recruiter repair now exhausts the five-call
budget before the critic (none did live).

## same-task-continuity

The twelve traps from the previous capsules hold. Three more:

1. **A stored contract does not re-project itself.** `_CATEGORY_DOMAINS`
   changes reach a store only through
   `reconcile_packaged_workforce_contracts` (run by `agency install`);
   `workforce_index_snapshot` reads the stored projection. Measure on a
   reconciled copy, never assume the live store carries branch vocabulary.
2. **`plan_policy_violations` must receive `known_domains`** beside
   `served_domains`, or a declared `novel_capability` unit naming its own
   domain is bounced back to the planner instead of reaching hiring.
3. **The recruiter-index size pin** in `test_workforce_selection_safety`
   changes whenever a domain promotion changes; update it with a dated note.

## next-bounded-work-package

In this order.

1. **AR-384 freeze and flip**: commit this branch, open the PR on #587,
   then in a second PR set `candidate_commit` to the implementation SHA,
   run `scripts/verify_acceptance.py --issue AR-384 --all --provider codex`,
   flip to `done`. AR-385 and AR-386 likewise (freeze to `0f70496c` and
   `6b79736c`).
2. **AR-373 residue**: `recruiter_candidate_row_shape_invalid` and evidence
   charset on first attempts, the `{}` repair reply (204) and the malformed
   941-token reply (304); the MiniMax deployment does not honour the strict
   `json_schema` `required` list.
3. **Recruiter authority blindness**: on plan units it ranks modify-authority
   implementers marked `execution_eligible: false` and leaves the eligible
   dual-domain planners unranked (201, 204); a prompt or repair-contract
   change, measured on the same eleven wordings.
4. **Recruiter timeout**: `agency-recruiter.timeout_ms` is the owner's; no
   call hit it this run (longest 17.9 s).
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

On the working tree before commit: ruff check and format clean on
`agency_runtime/core/workforce`, the evals module and the changed tests;
`tests/test_planner_domain_service.py` 13 passed; the twelve affected
workforce, receipt, intent and conformance suites 346 passed, 1 skipped
(before the novel-domain exemption; 120 passed on the three suites touched
after it); named fast spine 1004 passed, 3 skipped under `-W error`; `eval
routing` passed (1.4.0); decision-conformance rerun on the final tree
recorded in the ledger row; `docs_metadata.py --check`, `verify_docs.py`
green with the pending record. Pre-existing failures on the base are
unchanged.

## constraints

- `agency.yaml` is operator configuration: `strict_call_budget`, the
  recruiter `timeout_ms`, the deployment order and `workforce.mode` are the
  owner's call.
- Never commit to `main`; branch in a worktree, PR, merge with `--merge`.
  Ledger dance on every substantive commit. Tracker writes need
  authorization; AR-384, AR-385 and AR-386 carry `tracker_url: null`.
- The live store was not written by this session; a reconciled copy was.
