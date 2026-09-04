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
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar388-flip
evidence_commit: 13c483fbfa8646757ce9d51058da886a5a058b62
minimum_ledger_commit: 73181675389d6e7063298d7919e9e74b7b0c133b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `73181675` carries ADR-0198 to ADR-0204 and the done AR-373 and
> AR-384 to AR-388 (AR-388's flip rides on this PR). This refresh records the
> AR-388 close and the runtime reinstalled at that commit.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
recruiter sees the eligibility boundary it is held to (AR-387), an unset
gateway key is named at every layer instead of read as an outage (AR-388),
and the losses that remain are the critic's judgment and replies the
transport cannot read.

## checkpoint

**AR-388 is done** under **ADR-0204** (PR #599, flip on this branch): a
resolved planner or recruiter route is declared inference; the structured
transport answers a provider whose credential variable is unset with
`provider_credential_env_unset` instead of calling; the outcome, receipt and
disclosure carry `workforce_credential_env_unset`; `agency doctor` warns by
variable name listing the routed profiles. Verifier: four of four on the
first pass. **AR-387 is done** under **ADR-0203** (PRs #595 to #597): every
recall row carries the complete eligible card set, the safe-team repair
names the eligible coverers, and both prompts state the boundary.

- **AR-384 option 2** (ADR-0201): the planner sees the served domains per
  artifact kind and a unit with no served domain is bounced for repair.
- **AR-373 and AR-384 to AR-388 are done**; `verify_tracker.py` reports
  `missing_remote` for AR-384 to AR-388 until the owner authorizes their
  tracker issues, and #537 still needs its closure.
- **Install**: venv `73181675` built at the AR-388 merge. claude complete;
  codex `activation-required` (the owner's attended `Trust all and continue`
  in a fresh `codex` TUI, then `agency install --agent codex
  --verify-activation` with `common.env` sourced). Run `agency install`
  itself WITHOUT the key: the dashboard step refuses a service whose
  credentials live only in the process environment. hermes and openclaw
  not reinstalled.
- **Launch environment**: every inference profile reads `LITELLM_API_KEY`
  from the launching process's environment only, and nothing on the host
  exports it; on 2026-09-03 every preflight and both first codex
  verifications failed with a healthy gateway, passing at once with
  `~/.config/ai-secrets/common.env` sourced. AR-388 now names this.
- **Critic variance**: the turn-205 team replayed six times per prompt with
  the cache bypassed: 6 of 6 approved on one prompt, 1 of 6 on the other.

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
step and `--verify-activation` on venv `73181675`; tracker issues for AR-384
to AR-388 and closure of #537; the stale claude battery re-prove (`agency
battery` with `common.env` sourced). What remains in the runtime is judgment
and the deployment: three critic wrong-neighbour vetoes of eleven and two
replies the transport could not read.

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
2. **Critic wrong-neighbour judgment on install teams** (203, 205, 208): the
   critic's contract could carry the eligibility view too, so it does not
   veto the only eligible planners as wrong neighbours; measure on the
   eleven wordings with the cache-bypassing replay.
3. **Unreadable deployment residue** (no JSON object, omitted `score`,
   `decision` outside staff/gap): operator territory at the LiteLLM alias;
   recorded, not fixed.
4. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `13c483fb` (AR-388): new tests 7 passed; affected suites 267 passed, 1
skipped; named fast spine 1004 passed, 3 skipped under `-W error`;
decision-conformance 176 of 176 killed, tree unchanged; full suite in four
chunks: 93 failures identical on `main`, none unique to the branch; verifier
four of four on the first pass. AR-387's record verified on its second pass
at `b349e59b`. Activation on venv `56e0b6dd` was `runtime-verified` with the
key sourced; venv `73181675` awaits the owner's trust step.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
- Any live host invocation runs from a shell with
  `~/.config/ai-secrets/common.env` (mode 0600) sourced.
