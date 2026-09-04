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
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar389-flip
evidence_commit: ecde657481611dafc8a31a4fb6043dbdc9902dad
minimum_ledger_commit: 3ed000d42290f567b49fa65a54612c9f3b4268b9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `3ed000d4` carries ADR-0198 to ADR-0205 and the done AR-373 and
> AR-384 to AR-389 (AR-389's flip rides on this PR). This refresh records the
> AR-389 close and the runtime reinstalled at that commit.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
recruiter and the critic both see the eligibility boundary they are held to
(AR-387, AR-389), an unset gateway key is named at every layer instead of
read as an outage (AR-388), and the losses that remain are the recruiter's
fit judgment and replies the transport cannot read.

## checkpoint

**AR-389 is done** under **ADR-0205** (PRs #601 to #603, flip on this
branch): the critic document carries, per unit, the complete identity-sorted
eligible candidate list (bounded only by the roster's own limit) with its
count, compact cards for every eligible worker the recruiter ranked or
selected (bounded by the recruiter's own ranking limit), and whether the
selection is the whole neighbourhood; a
wrong-neighbour veto must name a card in it. Live on the
eleven wordings: completed 6 against 5, vetoes 3 against 3 on different
turns, both earlier vetoes approved, every veto naming an eligible card left
unselected. **AR-388** (ADR-0204, PR #599) names an unset credential at
every layer; **AR-387** (ADR-0203, PRs #595 to #597) gave the recruiter the
same boundary.

- **AR-384 option 2** (ADR-0201): the planner sees the served domains per
  artifact kind and a unit with no served domain is bounced for repair.
- **AR-373 and AR-384 to AR-389 are done**; `verify_tracker.py` reports
  `missing_remote` for AR-384 to AR-389 until the owner authorizes their
  tracker issues, and #537 still needs its closure.
- **Install**: venv `3ed000d4` built at the AR-389 close. claude
  complete and wired; codex `activation-required` (the
  owner's attended `Trust all and continue` in a fresh `codex` TUI, then
  `agency install --agent codex --verify-activation` with `common.env`
  sourced). Run `agency install` itself WITHOUT the key: the dashboard step
  refuses a service whose credentials live only in the process environment.
- **Launch environment**: every inference profile reads `LITELLM_API_KEY`
  from the launching process's environment only, and nothing on the host
  exports it; on 2026-09-03 every preflight and both first codex
  verifications failed with a healthy gateway, passing at once with
  `~/.config/ai-secrets/common.env` sourced. AR-388 now names this.
- **Critic judgment now has evidence**: the remaining vetoes name a card the
  recruiter ranked below its selection (the cross-platform release verifier
  on 202 and 205). The next lift is the recruiter's fit ranking, not the
  critic.

| eleven install wordings, strict mode, ADR-0203 runtime, store copy | turns |
|---|---|
| completed, critic approved | 5 (201, 204, 206, 207, 304); ADR-0202 run 4, ADR-0201 run 3, AR-386 run 2 |
| plan-authority units answered; ranked cards outside `eligible_candidate_ids` | 8; **0** |
| `staff_without_safe_team`, any unit | **0** (AR-386 run 5, ADR-0201 run 2) |
| critic `wrong-neighbor-selection` | 3 (203, 205, 208) |
| replies the transport could not read (no JSON object) | 2 (209 repair, 305) |
| reply shapes recorded and repaired (row shape, not a units object, `invalid_decision`) | 3 |

## completed-evidence

**On `main`.** ADR-0203 at `7af9c43b` (PR #595) and `b349e59b` (PR #596):
`_annotate_eligible_candidates`, `_eligible_coverers_by_requirement`, the
repair contract field, the prompt sentences,
`tests/test_recruiter_eligibility_view.py` (4 tests), one curated mutation,
`AR-387-evidence-20260903.txt` with both verifier passes; the frozen record
and done flip (PR #597). ADR-0202 at `760d631e` and `1c1bf079` (PR #591)
with `tests/test_recruiter_reply_residue.py` (16 tests) and AR-373 (#594).

**On the stack.** ADR-0201 at `7c67b524` (PR #588); the AR-384 and AR-386
flips (PRs #589, #590). **Capture recipe.** Scratchpad `capture387.py` to
`capture389.py` (a `_PlanPolicyValidationError` hook, `Store(db_path=<copy>)`),
`critic_replay.py` (patches `_http_payload` with `cache: {"no-cache": true}`),
store copy `agency.db.branch-copy` (generation 307), `PYTHONPATH=<worktree>`.

**Live facts worth keeping.** No `platform` or `desktop` on a plan unit in
33 turns; with the eligibility view the recruiter ranked only eligible cards
on every plan unit. The deployment still returns unreadable replies (209,
305), omits `score`, and once sent a `decision` outside staff/gap (304).

## exact-blocker

Nothing blocks at the contract level. Waiting for the owner: the codex trust
step and `--verify-activation` on venv `3ed000d4`; tracker issues for AR-384
to AR-389 and closure of #537; the stale claude battery re-prove (`agency
battery` with `common.env` sourced). What remains in the runtime is the
recruiter's fit ranking (three evidence-backed critic vetoes of eleven) and
the deployment (two replies the transport could not read).

## same-task-continuity

The previous capsules' traps hold. Three more:

1. **A stored contract does not re-project itself.** `_CATEGORY_DOMAINS`
   changes reach a store only through `reconcile_packaged_workforce_contracts`
   (`agency install`); measure on a reconciled copy.
2. **`plan_policy_violations` needs `known_domains`** beside `served_domains`,
   or a declared `novel_capability` unit is bounced back to the planner.
3. **Receipts re-project on read.** A row admitted only from a detail string
   vanishes when the receipt is read back; the list path must admit it too.
4. **The verifier reads "both prompts state X" literally.** Every prompt a
   criterion names must carry the criterion's phrase, not its consequence.
5. **Live host invocations need the key**: prefix `verify-activation`,
   `host-canary`, `battery` and the hosts with the `common.env` sourcing line;
   run `agency install` without it.
6. **Full-suite runs here carry ~93 pre-existing failures**; compare failing
   files against `main` under the same umask before attributing any.

## next-bounded-work-package

In this order.

1. **Owner steps**: codex `Trust all and continue`, then `agency install
   --agent codex --verify-activation` with the key sourced; tracker issues
   for AR-384 to AR-388 and closure of #537; `agency battery` (key sourced).
2. **Recruiter fit on verification units**: on 202 and 205 the recruiter
   required `evidence-collector` alone and left `cross-platform-release-
   verifier` acceptable; the critic now vetoes that with evidence. Measure
   whether the recruiter's document should name the unit's artifact kind
   against each card's artifact kinds more plainly; eleven wordings, replay.
3. **Unreadable deployment residue** (no JSON object, omitted `score`,
   `decision` outside staff/gap): operator territory at the LiteLLM alias;
   recorded, not fixed.
4. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `ecde6574` (AR-389): new tests 4 passed; affected suites and the
named fast spine green under `-W error`; decision-conformance 177 of 177
killed, tree unchanged; live eleven wordings on the branch runtime against
the baseline store copy (capture390); verifier four of four on the fourth
pass (absent for want of citations, then a cap of 64 against "complete",
then a bare 16 against "every ranked or selected worker"; both bounds are
now the runtime's own limits). AR-388 at `13c483fb`: four of four on the
first pass. Every flip so far verified `--all` satisfied.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
- Any live host invocation runs from a shell with
  `~/.config/ai-secrets/common.env` (mode 0600) sourced.
