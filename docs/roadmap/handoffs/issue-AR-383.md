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
> hosts from `c42fb0a5`; nothing is branch-only. One plain request staffed
> four units through the real hook against a store copy; live traffic since
> the install staffed nothing (14 of 14 runs `preflight_failed`). Open: the
> codex trust step (owner), the planner's prose replies, and AR-398.

Start-here capsule after the 2026-09-05 (early morning) session.

## checkpoint

**Merged with a merge commit:** PR #657 (`claude/ar397-acceptance`, ten
docs-only commits): the AR-397 close through the AR-361 flow, the platform
decision in AR-370, the AR-393 criterion 5 measurement, the AR-398 filing and
the review fixes. `main` did not move underneath it.

**Launch check held.** The claude ancestor process carried `LITELLM_API_KEY`;
every `launchers/current-<host>.json` names venv `c42fb0a5` (digest
`929576f2`); the plugin embeds that digest and claude started after the
install; `cli_install_drift_reports()` from the venv returns no report with cwd
outside the checkout (inside it, five foreign-package reports: the stale-import
trap, not drift).

**Codex is `activation-required`.** `agency install --agent codex
--verify-activation` with the key entered the canary path (no model call was
made) and stopped on `codex_hook_trust_not_ready`: hook trust
`status=modified observed=8 trusted=0`. The owner step is unchanged: a fresh `codex` terminal TUI and
`Trust all and continue`. One run failed the identity pre-check
without a canary; it did not reproduce in two later runs.

**AR-397 is done.** Record frozen at `45432976`, five `satisfied` verdicts in
one verifier round, 48 tests green at the candidate, the six pinning tests
failing on `dda2c8a3^`, the monitoring engineer covering `release` on a copy
of the live store. Per-slug tables decided as identity (first change for a
shipped slug pins the prior values beside the superseded contract; nothing to
pin today). Tracker #654 stays open until the owner authorizes its closure.

**Platform question settled from evidence.** The literal `install this:
https://zcode.z.ai/en` turn, driven through the real hook from `c42fb0a5`
against a store copy, was staffed on all four units with the critic approving;
the planner wrote `desktop`, `operations`, `quality-assurance` with `linux`
under `platforms`; the earlier install-a-CLI turn read the same minus
`desktop`. No reply used `platform`; the contracts keep `operations` alone.

## completed-evidence

Merged commits: `45432976` evidence, `32ab551a` verdicts and flip, `c93e8ae3`
platform decision, `57e4a265` AR-393 measurement and AR-398 filing,
`c9951209` review fixes, each with its `docs(worklog):` row. Session
`3a994fdc` scratchpad: `store-copy-b.db` (about 03:36Z; newest live receipt
03:35:41Z) holds the three hook probes, `store-copy-c.db` (03:59Z) proves the
live store took no row from them, `payloads-*/replies.jsonl` hold full replies.

**AR-393 criterion 5, measured on copies.** The first declaring receipt
written by fix-carrying code (2026-09-05T00:28:19Z, trace `381f75c6`) carries
`hiring_status_abstained`, `hiring_inference_attempted`,
`hiring_inference_failed`, `provider_model_text_not_json`; the 42 silent rows
all predate the fix. On the 03:59Z copy, 14 receipts since the `c42fb0a5`
install, none declaring; all 14 live runs in that window ended
`preflight_failed`, and the last live `ready` run is 2026-09-04T20:51Z.
Its second half asks pre-fix rows to name their condition; rewording is owner's.

**AR-398 (new, `open`, p1, tracker pending).** A COBOL z/OS request declared
six gap units; the hiring loop sent fifteen requests over 613 s (one security
review never returned; its 60 s deadline is part of the 613), every proposal
`hire`, every critic `approved`; the run's 600 s preflight lease expired at
03:56:02Z; `Store.fail_preflight_attempt` writes the receipt only inside an
UPDATE guarded by the lease, returned `False`, and `core/preflight.py:901`
discards it. Result: no receipt, no hiring case, the run left `in_progress`,
and the host told `no_safe_sufficient_team`. `renew()` serves child routes only.
Eleven live runs already sit in this shape (ten openclaw, one hermes).

## exact-blocker

**Three things, none of them code on a branch.** (1) Codex hook trust is an
attended step in a fresh TUI. (2) The planner's prose replies reproduced: five
turns in this session (03:34Z to 03:58Z) recorded `provider_model_text_not_json`
twice each on the planner (5.6 to 8.5 s, `actual_model` empty) and ended
`inference_unavailable`, 10 of the 14 live receipts in the window; receipts
store no prompt, so the shape is known only as "system-notification text as
the user message". (3) AR-398: a gap turn that outruns its lease vanishes.

## same-task-continuity

1. Import the installed package with cwd outside the checkout and `-P`
   (`cd <scratchpad> && <venv>/bin/python -P ...`); inside it the repo shadows
   the venv and every host reads as a foreign package.
2. Drive the real hook against a copy: add a `store:` block with `db_path:
   <copy>` to a copy of `agency.yaml` (the live file has none), pipe a hook
   JSON with a `diag-*` session id; `capture_full.py` keeps every full reply.
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
7. No venv rebuild is due (every merge was documentation); `build/` is cleared.
   The `c42fb0a5` venv and launcher tree still carry the retired
   `core/selector/domain_expansion.py`: nothing imports it, and the drift check
   cannot see it (it returns at once from an installed runtime, and the digest
   was computed over the tree that carries it). The next code merge drops it.

## verification

Branch gates at `a042df1a` and again at `367c93f3`: `verify_docs` 0 non-worklog
errors over 1056 documents, `docs_metadata`, `update_worklog --check` and
`update_policy_availability --check` clean, the two AR-397 suites 48 passed;
no Python changed, so ruff was not run. Verifier run ids
`AR-397.1..5-20260904-*`. One Opus review before the merge (186k tokens,
129 tool calls, 22 minutes): eight findings, five fixed in the branch, three
recorded here; a second pass on this capsule found a headline overclaim and
three wrong figures, fixed before merge. `agency doctor --fix-perms` repaired
425 group-writable and 224 non-private paths and still ends `FAILED` on
`harness_battery_claude` (`adapter_claude: not natively registered` is a
warning) while the claude hooks were demonstrably running.

## constraints

- `agency.yaml` is operator configuration (timeouts 60000, dated backup);
  deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host
  invocations need `common.env` sourced under `set -a`.
- Review passes: exactly one reviewer, pinned to Opus, artifacts only.
