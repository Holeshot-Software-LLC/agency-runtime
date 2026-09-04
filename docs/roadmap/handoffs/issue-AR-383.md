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
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar390-flip
evidence_commit: 15c404f374ec1d5c59bc58f7b65a52304d7eb8be
minimum_ledger_commit: 4bba2ff26bff11ab9b49eb8da009808796d98265
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `42916e4a` carries ADR-0198 to ADR-0206 and the done AR-373 and
> AR-384 to AR-390. This refresh records the AR-390 close, the runtime
> reinstalled at `e676e801` and the verified codex activation on it.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
recruiter and the critic both see the eligibility boundary they are held to
(AR-387, AR-389), every card carries every outcome (AR-390), an unset
gateway key is named at every layer (AR-388), and the losses that remain
are the recruiter's fit on review and plan units and unreadable replies.

## checkpoint

**AR-390 is done** under **ADR-0206** (PR #606, flip on this branch): the
compact recruiter card and the critic's neighbourhood card carry every
outcome and every `not_for` line, bounded only by the contract's own limits;
the card used to cut outcomes at two and every enabled contract declares at
least three. Live on the eleven wordings: the release verifier on the
verification unit in 7 of 8 critic-reached turns against 5 of 9; completed 4
against 6 inside a 5, 6, 4 spread (two unreadable replies, one budget
exhaustion, four vetoes now on review and plan units). **AR-389** (ADR-0205,
PRs #601 to #604) gave the critic the eligible neighbourhood; **AR-388**
(ADR-0204, PR #599) names an unset credential; **AR-387** (ADR-0203) gave
the recruiter the same boundary.

- **AR-384 option 2** (ADR-0201): the planner sees the served domains per
  artifact kind and a unit with no served domain is bounced for repair.
- **AR-373 and AR-384 to AR-390 are done**; `verify_tracker.py` reports
  `missing_remote` for AR-384 to AR-390 until the owner authorizes their
  tracker issues, and #537 still needs its closure.
- **Install**: venv `e676e801` built at the AR-390 close. claude complete
  and wired; codex `runtime-verified` with the attestation persisted after
  the owner's trust step. Each reinstall restages the hooks and needs the
  attended `Trust all and continue` in a fresh `codex` TUI, then `agency
  install --agent codex --verify-activation` with `common.env` sourced. Run
  `agency install` itself WITHOUT the key.
- **Launch environment**: every inference profile reads `LITELLM_API_KEY`
  from the launching process's environment only, and nothing on the host
  exports it; on 2026-09-03 every preflight and both first codex
  verifications failed with a healthy gateway, passing at once with
  `~/.config/ai-secrets/common.env` sourced. AR-388 now names this.
- **Where the vetoes point now**: review units staffed `test-results-analyzer`
  alone with `code-reviewer` and the release verifier ranked (203, 209), and
  plan units staffed `operations-manager` with the site reliability engineer
  ranked (305); the recruiter's fit judgment on those units is what remains.

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
33 turns; the recruiter ranked only eligible cards on every plan unit; the
deployment still returns unreadable replies (209, 305) and omits `score`.

## exact-blocker

Nothing blocks at the contract level. Both hosts run `e676e801`. Waiting for
the owner: tracker issues for AR-384 to AR-390 and closure of #537; the
stale claude battery re-prove (`agency
battery` with `common.env` sourced). What remains in the runtime is the
recruiter's fit on review and plan units (four evidence-backed critic vetoes
of eleven) and the deployment (two unreadable replies, one budget exhaustion).

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

1. **Owner steps**: tracker issues for AR-384 to AR-390 and closure of
   #537; `agency battery` from a shell with the key sourced.
2. **Recruiter fit on review and plan units**: 203 and 209 required
   `test-results-analyzer` alone on a review unit with `code-reviewer`
   ranked; 305 `operations-manager` on a plan unit with the SRE ranked.
   Replay with the cache bypassed first; the next candidate is the prompt's
   account of required versus acceptable on multi-card units.
3. **Unreadable deployment residue** (no JSON object, omitted `score`,
   `decision` outside staff/gap; two of eleven turns this run): operator
   territory at the LiteLLM alias; recorded, not fixed.
4. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `15c404f3` (AR-390): new tests 4 passed; affected suites 234 passed, 1
skipped; named fast spine 1004 passed, 3 skipped under `-W error`;
decision-conformance 178 of 178 killed, tree unchanged; live eleven wordings
on the branch runtime against the baseline store copy (capture391); verifier
four of four on the second pass. AR-389 at `ecde6574`: four of four on the
fourth pass. Every flip so far verified `--all` satisfied.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
- Any live host invocation runs from a shell with
  `~/.config/ai-secrets/common.env` (mode 0600) sourced.
