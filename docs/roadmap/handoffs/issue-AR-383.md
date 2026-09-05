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
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/decisions/0211-give-retrieval-a-subject-and-name-the-empty-turn.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: f706e8c60304578d381965b85b178ecf6071dbc3
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> Everything below is on `main` at `f706e8c6` and installed on all five
> hosts from `c42fb0a5`; nothing is branch-only. Staffing now completes on
> plain requests through the real hook; the open defects are the codex trust
> step (owner), the planner's prose replies, and a gap turn that loses its
> receipt (AR-398).

Start-here capsule after the 2026-09-05 (early morning) session.

## checkpoint

**Merged with a merge commit:** PR #657 (`claude/ar397-acceptance`, ten
docs-only commits): the AR-397 close through the AR-361 flow, the platform
decision in AR-370, the AR-393 criterion 5 measurement, the AR-398 filing and
the review fixes. `main` did not move underneath it.

**Launch check held.** The claude ancestor process carried `LITELLM_API_KEY`;
every `launchers/current-<host>.json` names venv `c42fb0a5` (digest
`929576f2`); this session's plugin embeds that digest and the claude process
started after the install; `cli_install_drift_reports()` from the venv returns
no report when run with cwd outside the checkout. Run inside the checkout it
returns five foreign-package reports: the stale-import trap, not drift.

**Codex is `activation-required`.** `agency install --agent codex
--verify-activation` with the key entered the canary path (no model call was
made) and stopped on `codex_hook_trust_not_ready`: hook trust
`status=modified observed=8 trusted=0`. The owner step is unchanged: a fresh `codex` terminal TUI and
`Trust all and continue`. One run failed the identity pre-check in 13 s
without a canary; it did not reproduce in two later runs.

**AR-397 is done.** Record frozen at `45432976`, five `satisfied` verdicts in
one verifier round, 48 tests green at the candidate, the five AR-397 tests and
the release-lifecycle test failing on `dda2c8a3^`, and the monitoring engineer
covering `release` on a copy of the live store. The per-slug table case is
decided: `_DOMAINS`, `_ARTIFACTS`, `_OPTIONAL_TOOLS` are identity and the first
change to one for a shipped slug must pin the prior values beside the
superseded contract; nothing to pin today. Tracker #654 stays open until the
owner authorizes its closure.

**Platform question settled from evidence.** The literal `install this:
https://zcode.z.ai/en` turn, driven through the real hook from `c42fb0a5`
against a store copy, was staffed on all four units with the critic approving;
the planner wrote `desktop`, `operations`, `quality-assurance` with `linux`
under `platforms`. The earlier install-a-CLI turn read `operations`,
`quality-assurance`, `linux`. No reply used `platform`; the contracts keep
`operations` alone (AR-370 doc, dated section).

## completed-evidence

Merged commits: `45432976` evidence, `32ab551a` verdicts and flip, `c93e8ae3`
platform decision, `57e4a265` AR-393 measurement and AR-398 filing,
`c9951209` review fixes, each with its `docs(worklog):` row. Store copies: `store-copy-b.db` (03:31Z) holds the
three hook probes; `store-copy-c.db` (03:59Z) proves the live store took no
row from them. Captures with full provider replies under
`scratchpad/payloads-{bareurl,gapcobol,gapada}` of session `3a994fdc`.

**AR-393 criterion 5, measured on copies.** The first declaring receipt
written by fix-carrying code (2026-09-05T00:28:19Z, trace `381f75c6`) carries
`hiring_status_abstained`, `hiring_inference_attempted`,
`hiring_inference_failed`, `provider_model_text_not_json`; the 42 silent rows
all predate the fix; 11 receipts since the `c42fb0a5` install, none declaring.
The criterion's second half asks pre-fix rows to name their condition, which
no code change can do; rewording it is an owner decision.

**AR-398 (new, `open`, p1, tracker pending).** A COBOL z/OS request declared
six gap units; the hiring loop sent fifteen requests over 613 s (one security
review never returned; its 60 s deadline is part of the 613), every proposal
`hire`, every critic `approved`; the run's 600 s preflight lease expired at
03:56:02Z; `Store.fail_preflight_attempt` writes the receipt only inside an
UPDATE guarded by the lease, returned `False`, and `core/preflight.py:901`
discards it. Result: no receipt, no hiring case, the run left `in_progress`,
and the host told `no_safe_sufficient_team`. `renew()` serves child routes only.
The live store already holds eleven runs in this shape (ten openclaw, one
hermes), read from the 03:59Z control copy.

## exact-blocker

**Three things, none of them code on a branch.** (1) Codex hook trust is an
attended step in a fresh TUI. (2) The planner's prose replies reproduced: two
task-notification turns in this session recorded `provider_model_text_not_json`
twice on the planner (6 to 8 s, `actual_model` empty) and ended
`inference_unavailable`; the receipts store no prompt, so the shape is known
only as "system-notification text as the user message". (3) AR-398: any gap
turn whose hiring loop outruns the lease vanishes from the store.

## same-task-continuity

1. Import the installed package with cwd outside the checkout and `-P`
   (`cd <scratchpad> && <venv>/bin/python -P ...`); inside it the repo shadows
   the venv and every host reads as a foreign package.
2. Drive the real hook against a copy: append `store:\n  db_path: <copy>` to a
   copy of `agency.yaml` (the live file has no store block), pipe a hook JSON
   with a `diag-*` session id, and patch `structured_provider._http_payload`
   and `_read_http_response` to keep full replies (`capture_full.py`).
3. `agency doctor --fix-perms` immediately before `verify_acceptance.py`; the
   npm tree goes group-writable again between sessions and the verifier then
   records nothing and exits 0.
4. A retrospective close binds `candidate_commit` to the evidence commit and
   cites the current tree; the verifier stamps the local date and bumps
   `evidence_cutoff` itself.
5. The codex identity pre-check can fail transiently on a cold inspector; run
   `--verify-activation` twice before reading "could not be proven".
6. Tracker gate is red between filing and mapping by design; run it with
   `--allow-open-complete` and read the warning, do not create issues.
7. One heredoc per shell call, printf commit messages to a file, `&&` after
   every gate, never pipe a gate through `tail`, merge with `--merge` only.

## next-bounded-work-package

1. Owner: fresh `codex` TUI, `Trust all and continue`, then
   `agency install --agent codex --verify-activation` with the key.
2. Owner: authorize closing #654 (AR-397 done) and creating the AR-398 tracker
   issue; then a "record the authorized tracker mapping" commit.
3. AR-398: implement approach items 1 and 2 (a refused close still leaves a
   receipt; the hiring loop stops inside the lease and says what it skipped),
   with a replay of the COBOL shape against a store copy as the live proof.
4. Capture one prose planner reply with its prompt: drive the hook with a
   task-notification-shaped message through `capture_full.py` and keep the
   payload; then decide whether the subject or plan prompt needs a JSON guard.
5. Owner decision: reword AR-393 criterion 5 to receipts written after the fix,
   then re-verify criterion 5 and flip AR-393.
6. Operator decision: glm-5-turbo cannot serve a plan call inside its 45 s
   deployment timeout, so the planner alias has one working deployment.
7. Nothing needs a venv rebuild: every merge this session was documentation.
   `build/` is cleared. The `c42fb0a5` venv and launcher tree still carry the
   retired `core/selector/domain_expansion.py` (nothing imports it, and the
   drift check compares projections, not trees); the next code merge rebuilds
   without it.

## verification

Branch gates at `a042df1a`: `verify_docs` 0 non-worklog errors over 1056
documents, `docs_metadata --check` clean, `update_worklog --check` current at
1801 commits, `update_policy_availability --check` exit 0, the two AR-397
suites 48 passed; no Python changed, so ruff was not run. Verifier run ids
`AR-397.1..5-20260904-*`. One Opus review before the merge (186k tokens,
129 tool calls, 22 minutes): eight findings, five fixed in the branch, three
recorded here. `agency doctor --fix-perms` repaired 425 paths and still ends
`FAILED` on `harness_battery_claude` and `adapter_claude: not natively
registered` while the claude hooks were demonstrably running.

## constraints

- `agency.yaml` is operator configuration; timeouts sit at 60000 with the
  dated backup. Deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host
  invocations need `common.env` sourced under `set -a`; `agency install` runs
  without the key.
- Review passes: exactly one reviewer, pinned to Opus, artifacts only.
