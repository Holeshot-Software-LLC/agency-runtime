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
> from venv `1c1efa07` (digest `5059543c`); nothing is branch-only except this
> capsule refresh (branch `claude/ar383-capsule-20260905d`, unpushed; if you
> read this from `main`, it merged and this note is spent). The live store is
> at schema 49. Claude and codex are live-proven on it (15:00Z); the hermes
> kernel (started 09-04) and zcode (09-02) still need a restart; the openclaw
> gateway restarted at 14:19:51Z and has no run since 09-02. The relaunched
> claude process has no `LITELLM_API_KEY`, so it cannot staff: relaunch it from
> a shell that sourced `common.env` under `set -a`.

Start-here capsule after the 2026-09-05 sessions (closes, codex trust, launch check).

## checkpoint

**Merged with merge commits, PRs #657 to #664:** AR-397 close and the AR-398
filing (#657); capsules (#658, #659, #662, #664); AR-398 lease receipt, schema
49 and ADR-0214 (#661); AR-399 trailing brace (#660); doctor check and record
flips (#663). One Opus review per PR (transcripts under `~/.claude/projects/`).

**Launch check 2026-09-05 15:00Z (session `2fced49c`).** claude pid 1880713
started 14:54:31Z; plugin cache `0.1.0+claude.6cd80ebeaf0f` installed 14:19:26Z;
all five launcher pointers and the codex and zcode hook commands name digest
`5059543c`; `cli_install_drift_reports()` from the 1c1efa07 venv (cwd `/tmp`,
`-P`) returns `()`. The hooks are proven live on the new install: this session's
first turn wrote run `1e4467cd` and receipt `8730a01c` into the schema-49 store
at 14:55Z. But `LITELLM_API_KEY` is absent from that process's environ (walked
up `ps -o ppid=`), so the planner attempt reads `provider_credential_env_unset`
and the receipt `workforce_provider_unavailable` with staffing codes
`inference_unavailable` and `workforce_credential_env_unset`. The codex TUI
(pid 1883778, started 14:55:31Z) lacks the key too.

**Codex is `runtime-verified` again (15:00Z).** Eight `trusted_hash` rows sit in
`~/.codex/config.toml`, and `agency install --agent codex --verify-activation
--json` from the 1c1efa07 venv with the key sourced returned `ok` and
`complete` with `installation_attempted: false` (canary run `19ca4773`,
14:59:44Z to 15:00:53Z, `code-reviewer` staffed). One ordinary `codex exec`
turn from the sourced shell (run `6c3bd716`, 15:01:26Z to 15:03:24Z, routing
latency 96 s) staffed five units by inference: planner, dense recall, recruiter
and critic `structured_response_applied`; one local recall attempt on
`qwen3-14b-abliterated` rejected `provider_response_contract_invalid`; five
specialists loaded; header `Recruited via: inference`; no gap, so no hiring
account was owed.

**AR-397 is done** (record at `45432976`, five verdicts). Tracker #654 stays
open until the owner authorizes its closure. Platform settled as `operations`.

**AR-398 and AR-399 done** (PR #663; records frozen at `2ae2b9c2` and
`894be044`): token-guarded close with `preflight_lease_expired_before_close`,
lease-bounded hiring loop with `hiring_lease_budget_exhausted`, schema 49,
hiring codes carried one at a time (`hiring_reason_code_invalid` for the
uncarriable, the first named AR-393 silence condition), doctor
`db_preflight_stuck`; a plan object plus stray brackets is parsed and the
attempt records `model_text_trailing_data_trimmed`.

## completed-evidence

Merged commits on `main`: AR-397 close `45432976`..`c9951209`; capsules
`23ef5f01`, `257ebd39`, `eb035aaa`, `769488e7`, `ba7acc86`, `994bd706`,
`fd01e782`; AR-398 `b1cc2612`, `424e56be`, `2ae2b9c2`, `40e5ac76`; AR-399
`cfc4e166`, `894be044`; each with its `docs(worklog):` row. Session `3a994fdc`'s
scratchpad holds the AR-398 replays and `capture_full.py`, `capture_hiring.py`.
Session `2fced49c`'s scratchpad holds `store-copy-a.db` (14:56Z),
`store-copy-b.db` (15:03Z), `doctor-1c1efa07.txt`,
`codex-verify-activation.json`, and `codex-ordinary/exec-out.txt`.

**The new receipt codes are still unobserved live.** On the 15:03Z copy, 0 of
1123 receipts carry `model_text_trailing_data_trimmed`,
`hiring_lease_budget_exhausted`, `preflight_lease_expired_before_close` or
`hiring_reason_code_invalid`: both codex turns were fully staffed with a clean
plan, the claude turn never reached the planner, and no other host has a run
since the install (hermes 09-04, zcode 09-05 12:59Z, openclaw 09-02).

**db_preflight_stuck (installed 1c1efa07 CLI, 14:58Z): 11** (hermes 1, openclaw
10), unchanged. The same run flags the key unset in its shell,
`harness_battery_claude` failed (09-02 receipt), fourteen group-writable npm dirs.

**AR-393 criterion 5, measured on copies.** The first declaring receipt written
after the fix (2026-09-05T00:28:19Z) carries a four-code hiring account; the 43
silent rows predate the projector fix, and no code change can make them name
their condition. Not reworded as of `424e56be`; rewording is the owner's.

## exact-blocker

**Nothing is code on a branch; the live proof waits on owner steps.** (1) The
relaunched claude process has no gateway key: relaunch it from a shell that ran
`set -a; . ~/.config/ai-secrets/common.env; set +a` (the file has no `export`
lines). (2) The hermes kernel (started 09-04) and zcode (09-02) still run the
old runtime, which refuses the schema-49 store; restart both. openclaw is
unproven, not stuck. (3) Tracker writes: #654 is still open and no AR-398 or
AR-399 issue exists; `verify_tracker.py` reports exactly `missing_remote=
['AR-398', 'AR-399']` and `AR-397: tracker state OPEN != CLOSED`, by design.
(4) Criterion 5 of AR-393 is not reworded, so it was not re-verified.

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
5. One heredoc per shell call, printf commit messages to a file, `&&` after
   every gate, never pipe a gate through `tail`, merge with `--merge` only;
   measure lint parity from the main checkout, not from the worktree.
6. Copy the live store with the sqlite backup API from a `mode=ro` URI (no
   `sqlite3` binary on this box); drive a codex turn with `codex exec
   --skip-git-repo-check -C <dir> "<prompt>"` from a sourced shell.

## next-bounded-work-package

1. After the keyed claude relaunch and the hermes and zcode restarts, drive one
   ordinary turn per host and read the first receipts from a store copy; then
   one gap turn (a prompt no roster card covers) on a keyed host: a populated
   hiring account and, if the lease bound fires, `hiring_lease_budget_exhausted`.
2. Owner: authorize closing #654 and creating the AR-398 and AR-399 tracker
   issues; then the "record the authorized tracker mapping" commit.
3. Owner decision: reword AR-393 criterion 5 to receipts written after the fix;
   then re-verify it through the AR-361 flow.
4. Codex: a reinstall changes its eight hook hashes and demands the trust
   screen again; re-run the verify-activation canary after any install.
5. Operator decision: glm-5-turbo cannot serve a plan call inside its 45 s
   deployment timeout (the planner alias has one working deployment).

## verification

Install: venvs `e52f849e` then `1c1efa07` built from the checkout; all five
pointers and the claude plugin cache on digest `5059543c`; drift call empty from
outside the checkout; live store migrated 48 to 49 with the receipt table's four
triggers intact; safety copy `live-store-before-install-132442.db`. Live: claude
run `1e4467cd` (keyless), codex runs `19ca4773` and `6c3bd716` (staffed), all
read from copies. Per PR at merge: test and lint parity for #660, #661 and #663
are in their worklog rows; docs gates clean including worklog rows on all.

## constraints

- `agency.yaml` is operator configuration (timeouts 60000 and 120000, dated
  backup); deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host calls
  and host launches need `common.env` sourced under `set -a`.
- The `agency` shim on PATH still runs venv `04adb230`; call
  `~/.local/share/agency-runtime/venvs/1c1efa07/bin/agency` directly.
- Review passes: exactly one Opus reviewer per checkpoint, artifacts only.
