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
evidence_commit: 1c1efa0777a0c7388297e7302aa41174952de7a3
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> Everything below is on `main` at `1c1efa07` and installed on all five hosts
> from venv `1c1efa07` (digest `5059543c`); nothing is branch-only. The live
> store is at schema 49, and a runtime still on `c42fb0a5` refuses it ("schema is
> newer than this runtime (49 > 48)"): relaunch claude, restart hermes and
> zcode, and trust the eight codex hook events once more in a fresh TUI. The
> install restarted the openclaw gateway (14:19:51Z); no host is live-proven yet.

Start-here capsule after the 2026-09-05 sessions (close, codex trust, two fixes,
doctor check, AR-398 and AR-399 done).

## checkpoint

**Merged with merge commits:** PR #657 (AR-397 close, platform decision, AR-393
measurement, AR-398 filing), #658 and #659 (capsule), then #661
(`claude/ar398-lease-receipt`: token-guarded close, lease-bounded hiring loop,
schema 49, hiring codes carried one at a time, ADR-0214), #660
(`claude/ar399-trailing-brace`: a plan object plus one stray brace is parsed and
the repair named), #662 (capsule), #663 (`claude/ar398-doctor-stuck-runs`: doctor
check, records frozen and flipped). One Opus review per PR (transcripts: session
`3a994fdc`'s `subagents/agent-*.jsonl` under `~/.claude/projects/`, not GitHub).

**Launch check held twice** on the same claude process (`c42fb0a5`, key in the
environ, plugin digest `929576f2`; drift empty from outside the checkout only).

**Codex was `runtime-verified` at 11:35Z and is `activation-required` again**
after each reinstall changed its eight hook hashes (`status=modified observed=8
trusted=0` under 1c1efa07); the owner's `Trust all and continue` in a fresh TUI,
then `agency install --agent codex --verify-activation` with the key, repeats
the 11:35Z result. The only codex turn so far was the canary itself. Note the
`agency` shim on PATH (`~/.local/bin/agency`) still runs venv `04adb230`; use
`~/.local/share/agency-runtime/venvs/1c1efa07/bin/agency` for live commands.

**AR-397 is done** (record at `45432976`, five verdicts, per-slug tables decided
as identity). Tracker #654 stays open until the owner authorizes its closure.

**Platform settled:** two real planner turns wrote `operations` (plus the
subject's own domain) with linux under `platforms`; no `platform` domain.

**AR-398 done** (PR #663): token-guarded close with `preflight_lease_expired_before_close`,
lease-bounded hiring loop with `hiring_lease_budget_exhausted`, schema 49, hiring
codes carried one at a time, and `agency doctor`'s `db_preflight_stuck`, which the
installed 1c1efa07 CLI runs live against the real store: eleven attempts stuck
since 2026-08-22 (ten openclaw, one hermes). Four verdicts satisfied; record
frozen at `2ae2b9c2` with criterion 3 reworded and re-verified.

**AR-399 done** (PR #663): a complete plan object plus stray closing brackets is
parsed and the attempt records `model_text_trailing_data_trimmed`; twelve tests;
record frozen at `894be044`, four verdicts satisfied.

**AR-393's silence, first condition named.** `preflight_hiring_reason_codes`
returned `[]` for a whole turn when one code failed the identifier rule, and the
hiring module raises `contract_invalid:<detail>` with a colon; a replay showed six
hiring events projecting to nothing. Fixed in #661 (codes carried one at a
time, `hiring_reason_code_invalid` for the uncarriable). Not proven to explain all
43 rows.

## completed-evidence

Merged commits on `main`: AR-397 close `45432976`..`c9951209`; capsules
`23ef5f01`, `257ebd39`, `eb035aaa`, `769488e7`, `ba7acc86`; AR-398 `b1cc2612`,
`424e56be`, `2ae2b9c2` (doctor check), `40e5ac76` (review fixes); AR-399
`cfc4e166`, `894be044`; each with its `docs(worklog):` row. Scratchpad of
session `3a994fdc`: `store-copy-b.db` holds the original 03:46Z loss (trace
`66d5588b`, no receipt, run `in_progress`, lease expired 03:56:02Z); copies e, f,
g, h hold the four AR-398 replays, g with `payloads-plifix3/projector.jsonl` (six
events in, `[]` out) and h with the fixed receipt; `payloads-notif1/2` hold the
four stray-brace replies; `store-copy-c.db` (03:59Z) is the untouched control.
`capture_full.py` keeps full provider replies; `capture_hiring.py` dumps hiring
events and the projector's input and output.

**AR-393 criterion 5, measured on copies.** The first declaring receipt written by
fix-carrying code (2026-09-05T00:28:19Z) carries a four-code hiring account; the
43 silent rows (the 43rd at 12:52Z, written by this session's un-relaunched
`c42fb0a5` hooks) all come from runtimes without the projector fix; its second half asks pre-fix rows to name
their condition, which no code change can do. Rewording is the owner's.

## exact-blocker

**Nothing is code on a branch; the live proof waits on owner steps.** (1) The
old runtime refuses the schema-49 store: this claude process (hooks on
`c42fb0a5`) wrote nothing after 13:25Z, and the hermes kernel (started 09-04)
and zcode processes (started 09-02) are in the same state; relaunch claude and
restart hermes and zcode. The install restarted the openclaw gateway, which has
no run since 09-02: unproven, not stuck. (2) Codex hook trust, as above. (3)
Tracker writes: closing #654 (AR-397 done) and creating issues for AR-398 and
AR-399; the tracker gate is red until then, by design.

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
5. A retrospective close binds `candidate_commit` to the evidence commit; rows
   of a pending record are validated against the working tree, so compute line
   ranges from the files; read a frozen record's ranges at its `candidate_commit`.
6. Duck-typed requests (the canary path, tests) predate new request fields:
   read them with `getattr(..., None)`.
7. One heredoc per shell call, printf commit messages to a file, `&&` after
   every gate, never pipe a gate through `tail`, merge with `--merge` only;
   measure lint parity from the main checkout, not from the worktree.

## next-bounded-work-package

1. After the relaunches, read the first live receipts from a store copy, one per
   host including openclaw: a rescued plan carries `model_text_trailing_data_trimmed`
   on its planner attempt; a gap turn carries a populated hiring account and, when
   the lease bound fires, `hiring_lease_budget_exhausted`. `build/` is clear.
2. Owner: authorize closing #654 and creating the AR-398 and AR-399 tracker
   issues; then the "record the authorized tracker mapping" commit.
3. Owner decision: reword AR-393 criterion 5 to receipts written after the fix;
   then re-verify it. The projector condition is named; whether the 42 rows'
   turns carried `contract_invalid:` codes is not recoverable from receipts.
4. Codex: after trust, drive one ordinary turn and read whether it staffs.
5. Operator decision: glm-5-turbo cannot serve a plan call inside its 45 s
   deployment timeout (the planner alias has one working deployment).

## verification

Install: venvs `e52f849e` then `1c1efa07` built from the checkout; all five
pointers and the claude plugin cache on digest `5059543c`; drift call empty from
outside the checkout; live store migrated 48 to 49 with 1122 receipts and the
receipt table's four triggers (`immutable`, `scope_insert`, two `_activity`)
intact; safety copy `live-store-before-install-132442.db`.
Per PR at merge: #661 16 new tests, 463 passed across 18 files, lint 10
findings repo-wide against main's 11; #660 10 new tests, 827 passed across
33 files with six failures identical on main, lint identical to main; #663 two
doctor tests, its two failures pre-existing on main; docs gates clean including
worklog rows on all. Review findings are folded in or recorded here.

## constraints

- `agency.yaml` is operator configuration (timeouts 60000 and 120000, dated
  backup); deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host calls
  need `common.env` sourced under `set -a`.
- Review passes: exactly one Opus reviewer per checkpoint, artifacts only.
