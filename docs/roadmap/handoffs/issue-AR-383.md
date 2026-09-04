---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-04
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-391-recruiter-prompt-misstates-how-its-ranking-becomes-the-team.md
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: 169220ce9978858b9101b348d35eeea2d776c094
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `b1c2b557` carries ADR-0198 to ADR-0208. AR-383 and AR-391 both
> closed on 2026-09-04; the recruiter's fit losses and the dense-recall loss
> that named this capsule are fixed and measured.

Start-here capsule. The planner side is closed, the recruiter reads its own
selection rule, the critic sees the neighbourhood it judges, every card
carries every outcome, the inferred subject reaches recall, and what remains
is the deployment behind the aliases and the owner's tracker steps.

## checkpoint

**AR-391 is done** under **ADR-0207** (PRs #611 to #616). The recruiter
classified one card required and the rest acceptable because its prompt called
an acceptable card one "the runtime may add when needed" and told it not to
label every strong candidate required. The runtime adds acceptable cards only
as typed-coverage complements, reads the ranking as order alone, and takes a
unit's confidence from the lowest selected rank score. On the review units the
one eligible coverer of `capability:risk-analysis` sat at rank four or five,
the verifier rejected the faithful team as `selection_confidence_too_low` with
a bare code, and the repair inverted it into that coverer alone, which the
critic vetoed correctly. Now the contract states the derivation with the
verifier's own numbers, each recall row names its `sole_eligible_coverers`,
both prompts state the rule, a whole-team rejection hands back the derived
team beside a correction, and the fit account names `not_for`.

**AR-383 is done** under **ADR-0208** (PRs #617 and its flip). ADR-0197 merged the
inferred subject into the projected turn context; on a fresh turn that context
is empty, so the merge made a single-key mapping the projection refuses, the
per-unit recall query raised, and the exception was discarded. The subject now
rides beside the context and reaches the planner document, the recall query and
the recruiter document as `inferred_work_subject`; a refused projection names
the validation that refused it with a closed code the attempt and the receipt
keep.

| measurement | before | after |
|---|---|---|
| eleven install wordings: completed | 4 | 9 |
| of the turns that reached the critic: approved | 4 of 8 | 9 of 9 |
| offline review-unit replies the verifier accepts | 1 of 6 | 6 of 6 |
| thirty-prompt smoke: subject-stage turns | 17 | 17 |
| of those, dense recall lost to a refused projection | 17 | **0** |

- **Install**: venv `04adb230` (merged main) built at the AR-383 close; claude
  installed and wired. Run `agency install` itself WITHOUT the key; codex needs
  the attended `Trust all and continue` in a fresh `codex` TUI, then `agency
  install --agent codex --verify-activation` with `common.env` sourced.
- **Launch environment**: still the first thing to check. `/clear` reuses the
  running process, so a key exported after launch never reaches the hooks; read
  `/proc/<pid>/environ` before suspecting the gateway. A session whose staffing
  header reads unavailable with a healthy gateway is that, every time.

## completed-evidence

**On `main`.** ADR-0207 at `d3bea30f` (PR #611) with
`tests/test_team_derivation_account.py` (6 tests) and two curated mutations,
corrected at `2c092cb8` (#612), `606e70ea` (#614) and `3a94b8da` (#615), record
rows recomputed in #613, flipped in #616. ADR-0208 at `169220ce` (PR #617) with
`tests/test_inferred_subject_beside_context.py` (6 tests) and two curated
mutations. **Capture recipe.** Scratchpad `capture392.py` (a copy of 391 reading
`common.env`), `recruiter_replay_h.py` (`--system`, `--contract`, `--annotate`;
sends `cache: {"no-cache": true}`), `derive_h.py` (a reply through
`_proposal_from_nominations` and `verify_staffing` on the store copy),
`smoke383.py` (the thirty-four prompt route smoke), store copy
`agency.db.branch-copy` (generation 307), `PYTHONPATH=<worktree>`.

## exact-blocker

Nothing blocks at the contract level. Waiting for the owner: tracker issues for
AR-384 to AR-391, closure of #537, and `agency battery` from a shell with the
key sourced. What remains in the runtime is the deployment behind the aliases.

## deployment-residue

Two causes, separated on 2026-09-04 and previously read as one shape:

1. **The runtime's timeout is below the gateway's.** Every workforce profile in
   `agency.yaml` carries `timeout_ms: 30000`; every deployment behind
   `task-agency-planner-v2`, `task-agency-recruiter-v2` and
   `task-agency-critic-v2` carries `timeout: 45.0`. A call answered between 30
   and 45 seconds is aborted by the runtime's own socket deadline, so no body
   arrives. Seen at exactly 30.04 s on capture391 turn 201 and capture392 turn
   205 (twice).
2. **One deployment emits a misplaced brace.** capture391 turn 206: HTTP 200,
   5330 characters from `b0b6f29c` (MiniMax-M3, order 1 behind the recruiter
   alias), failing at character 257 because a candidate object closes before its
   `score`. Not a completion-cap cut; the body ends complete.

Both reach the receipt as one code. `structured_provider` catches every
transport exception and returns `None`, and the stage loop records
`provider_no_valid_response`, so a timeout the runtime itself caused is
indistinguishable from a malformed reply. That is the AR-388 and AR-304 shape
in a fourth place, filed as AR-392: name the timeout on the attempt, and set
`timeout_ms` and the deployment timeout in the right order (operator
configuration either way).

## same-task-continuity

The previous capsules' traps hold. Four more:

1. **Write a release chain as one `&&` chain and never pipe a gate through
   `tail`.** Both slipped on 2026-09-04: a `;` after the docs gate merged PR
   #612 without its record update, and a `tail` after pytest merged PR #614
   with a failing test. Gate on the filtered error list with `test -z`.
2. **The isolated verifier reads a criterion's phrase literally, in every
   prompt the criterion names.** AR-391 needed three passes for one criterion:
   "Required is the team" (pass 1) and "the sole coverer directly after the
   team it completes" (pass 2) each had to appear in the repair prompt itself,
   not only in its consequence.
3. **A phrase split across adjacent string literals still counts**, both to the
   verifier and to a test that asserts against the assembled constant; a check
   that greps single source lines will report a false absence.
4. **A long live run and the conformance eval cannot share a tree.** The eval
   mutates sources in place; anything importing that checkout mid-run reads a
   mutated module. Sequence them.

## next-bounded-work-package

In this order.

1. **Owner steps**: tracker issues for AR-384 to AR-392, closure of #537, and
   `agency battery` with the key sourced.
2. **Implement AR-392**, filed 2026-09-04 from the residue above: the receipt
   cannot tell a runtime timeout from a malformed reply.
3. **The 4-of-5 gap divergence**, then **AR-370**.

## verification

At `169220ce` (AR-383): new tests 6; affected suites 493 passed, 10 skipped;
named fast spine 1165 passed, 3 skipped under `-W error`; mutation snippets
182; decision-conformance 182 of 182 killed, tree unchanged; the thirty-four
prompt smoke re-run on the branch runtime through the same read-only `agency
route` surface as the 2026-09-03 measurement. At `d3bea30f` and its three
corrections (AR-391): new tests 6; affected 239; spine 1165; conformance 180 of
180; the eleven install wordings live against the reconciled store copy;
verifier six of six on the third pass.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
- Any live host invocation runs from a shell with
  `~/.config/ai-secrets/common.env` (mode 0600) sourced.
