---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-05
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner, install]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-397-packaged-contracts-cannot-be-revised-in-place.md
  - docs/roadmap/issue-AR-398-a-gap-turn-that-outruns-its-lease-leaves-no-receipt.md
  - docs/roadmap/issue-AR-399-a-plan-object-followed-by-a-stray-brace-reads-as-prose.md
  - docs/decisions/0214-close-a-preflight-attempt-on-its-token-not-its-lease.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/decisions/0211-give-retrieval-a-subject-and-name-the-empty-turn.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: e52f849e573f846201a5cf03b11fccb27ac2fa4a
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> Everything below is on `main` at `e52f849e` and installed on all five hosts
> from venv `e52f849e` (digest `769b06ad`); nothing is branch-only. The live
> store is at schema 49, and a runtime still on `c42fb0a5` refuses it ("schema is
> newer than this runtime (49 > 48)"), so until claude is relaunched and hermes
> and zcode restarted their hooks fail at store open. Codex needs its trust step.

Start-here capsule after the 2026-09-05 sessions (close, codex trust, two fixes).

## checkpoint

**Merged with merge commits:** PR #657 (AR-397 close, platform decision, AR-393
measurement, AR-398 filing), #658 and #659 (capsule), then #661
(`claude/ar398-lease-receipt`: token-guarded close, lease-bounded hiring loop,
schema 49, hiring codes carried one at a time, ADR-0214) and #660
(`claude/ar399-trailing-brace`: a plan object plus one stray brace is parsed and
the repair named). Each PR had one Opus review (a subagent, not recorded on
GitHub) before merge.

**Launch check held twice** on the same claude process (`c42fb0a5`, key in
the environ, plugin digest `929576f2`, drift call empty from outside the
checkout; inside it, five foreign-package reports: the stale-import trap).

**Codex was `runtime-verified` at 11:35Z and is `activation-required` again**
since the e52f849e install changed its eight hook hashes (`status=modified
observed=8 trusted=0`); the owner's `Trust all and continue` in a fresh TUI,
then `agency install --agent codex --verify-activation` with the key, repeats
the 11:35Z result. The only codex turn so far was the canary itself.

**AR-397 is done** (record at `45432976`, five verdicts, per-slug tables decided
as identity). Tracker #654 stays open until the owner authorizes its closure.

**Platform settled:** two real planner turns wrote `operations` (plus the
subject's own domain) with linux under `platforms`; no `platform` domain.

**AR-398 fixed (in_progress; doctor count open).** The close is guarded by the
attempt token alone and names an expired lease as `preflight_lease_expired_before_close`;
the hiring loop stops when the lease cannot fit another round (floor one provider
deadline, raised to the longest measured round, 10 s margin) and marks skipped
units `hiring_lease_budget_exhausted`; schema 49 rebuilds pre-49 receipt tables.
Four replays against store copies: the last closed at 390 s with seven hiring
codes on its receipt. Pending record; criterion 4 (`agency doctor` counts stuck
runs) not done.

**AR-399 fixed (in_progress).** Every captured prose reply was a complete plan
object plus one stray `}`; the parser keeps the first complete object when only
closing brackets, fence ticks or whitespace follow and the applied attempt records
`model_text_trailing_data_trimmed`. Ten tests; the neighbourhood's six failures
are main's own. Pending record.

**AR-393's silence, first condition named.** `preflight_hiring_reason_codes`
returned `[]` for a whole turn when one code failed the identifier rule, and the
hiring module raises `contract_invalid:<detail>` with a colon; a replay showed six
hiring events projecting to nothing. Fixed in #661 (codes carried one at a
time, `hiring_reason_code_invalid` for the uncarriable). Not proven to explain all
43 rows.

## completed-evidence

Merged commits on `main`: AR-397 close `45432976`..`c9951209`; capsules
`23ef5f01`, `257ebd39`, `eb035aaa`; AR-398 `b1cc2612` and `424e56be`; AR-399
`cfc4e166`; each with its `docs(worklog):` row. Session `3a994fdc` scratchpad:
`store-copy-b.db` holds the original 03:46Z loss (trace `66d5588b`, no receipt,
run `in_progress`, lease expired 03:56:02Z); copies e, f, g, h hold the four AR-398
replays, g with `payloads-plifix3/projector.jsonl` (six events in, `[]` out) and
h with the fixed receipt; `payloads-notif1/2` hold the four stray-brace replies;
`store-copy-c.db` (03:59Z) is the untouched control. `capture_full.py` keeps full
provider replies; `capture_hiring.py` dumps hiring events and the projector's
input and output.

**AR-393 criterion 5, measured on copies.** The first declaring receipt written by
fix-carrying code (2026-09-05T00:28:19Z) carries a four-code hiring account; the
43 silent rows (the 43rd at 12:52Z, written by this session's un-relaunched
`c42fb0a5` hooks) all come from runtimes without the projector fix; its second half asks pre-fix rows to name
their condition, which no code change can do. Rewording is the owner's.

## exact-blocker

**Nothing is code on a branch; the live proof waits on owner steps.** (1) The
old runtime refuses the schema-49 store: this claude process (hooks on
`c42fb0a5`) wrote nothing after 13:25Z, and the hermes kernel (started 09-04)
and zcode processes (started 09-03) are in the same state; relaunch claude and
restart hermes and zcode. (2) Codex hook trust, as above. (3) Tracker writes:
closing #654 (AR-397 done) and creating issues for AR-398 and AR-399; the tracker
gate is red until then, by design.

## same-task-continuity

1. Import the installed package with cwd outside the checkout and `-P`
   (`agency_runtime.core.runtime_staleness.cli_install_drift_reports`); to run
   branch code live, `PYTHONPATH=<worktree> <venv>/bin/python -P capture_*.py
   hook claude --event UserPromptSubmit --config <copy.yaml> < hook-in.json`,
   the config copy carrying a `store:` block (the live file has none).
2. Identical prompts are gateway cache hits (planner and recruiter replay in a
   second); change the wording to measure again, keep it to reach the same gap.
3. A gap turn with six units costs 8 to 10 minutes of hiring inference; the
   lease bound now ends it with a receipt, but budget the wall clock.
4. `agency doctor --fix-perms` immediately before `verify_acceptance.py`; the
   npm tree goes group-writable again between sessions.
5. A retrospective close binds `candidate_commit` to the evidence commit; a
   pending record's rows are validated against the working tree, so compute
   line ranges from the files, never from memory.
6. Duck-typed requests (the canary path, tests) predate new request fields:
   read them with `getattr(..., None)`.
7. One heredoc per shell call, printf commit messages to a file, `&&` after
   every gate, never pipe a gate through `tail`, merge with `--merge` only;
   measure lint parity from the main checkout, not from the worktree.

## next-bounded-work-package

1. After the relaunch, read the first live receipts from a store copy: a rescued
   plan carries `model_text_trailing_data_trimmed` on its planner attempt; a gap
   turn carries a populated hiring account and, when the lease bound fires,
   `hiring_lease_budget_exhausted`. `build/` is cleared again after this build.
2. Owner: authorize closing #654 and creating the AR-398 and AR-399 tracker
   issues; then the "record the authorized tracker mapping" commit.
3. AR-398 criterion 4: `agency doctor` reports runs left `in_progress` past their
   lease (eleven live, all 2026-08-22 to 08-31, ten openclaw and one hermes); then freeze both pending records, run the isolated
   verifier, flip AR-398 and AR-399 to done.
4. Owner decision: reword AR-393 criterion 5 to receipts written after the fix;
   then re-verify it. The projector condition is named; check whether the 42
   rows' turns carried `contract_invalid:` codes is not recoverable from receipts.
5. Codex: after trust, drive one ordinary turn and read whether it staffs.
6. Operator decision: glm-5-turbo cannot serve a plan call inside its 45 s
   deployment timeout (the planner alias has one working deployment).

## verification

Install: venv `e52f849e` built from the checkout in 5 s, all five pointers and
the claude plugin cache on digest `769b06ad`, `cli_install_drift_reports()` empty
from outside the checkout, the live store migrated 48 to 49 with 1122 receipts
and all four triggers intact (safety copy `live-store-before-install-132442.db`).
Per PR at merge: #661 16 new tests, 463 passed across 18 files, lint 10
findings repo-wide against main's 11; #660 10 new tests, 827 passed across
33 files with six failures identical on main, lint identical to main; docs gates
clean including worklog rows on both. Two Opus reviews (one per PR) before merge;
their findings are folded in or recorded here.

## constraints

- `agency.yaml` is operator configuration (timeouts 60000 and 120000, dated
  backup);
  deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host calls
  need `common.env` sourced under `set -a`.
- Review passes: exactly one Opus reviewer per checkpoint, artifacts only.
