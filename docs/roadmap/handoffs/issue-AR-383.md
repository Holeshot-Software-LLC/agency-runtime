---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-04
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner, install]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-397-packaged-contracts-cannot-be-revised-in-place.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/decisions/0211-give-retrieval-a-subject-and-name-the-empty-turn.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: 573849767e46d2563fa82350eab951838de4033c
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> Everything below is on `main` at `57384976` and installed on all five
> hosts from `c42fb0a5`. Nothing is branch-only. Staffing still dies at the
> planner and recruiter most turns; that is the blocker, and it is not code on
> any branch.

Start-here capsule after the 2026-09-04 evening session.

## checkpoint

**Merged in order with merge commits:** #632 AR-395, #633 AR-394 (ADR-0213),
#634 AR-392, #635 AR-370 c1 finding, #636 AR-393 c5, #637 capsule, then #638
(the two operations contracts), #639 (its review follow-up), #640 (AR-397 plus
the monitoring `release` lifecycle) and the tracker-mapping PR. Each merge-back
of `main` carried a `docs(worklog):` row. The capsule's old conflict list was
incomplete: #633 and #634 also met in `receipt_projection.py`; both kept.

**Install is live on every host.** `cli_install_drift_reports()` from the
`c42fb0a5` venv returns no report, and every `launchers/current-<host>.json`
names that venv. openclaw reads `runtime-verified`; hermes and zcode
`enabled-runtime-unverified` until a live turn; codex `activation-required`
because the new hook inventory (8 events, `status=modified trusted=0`) must be
trusted in a fresh `codex` TUI. The claude session that did the work still runs
the old runtime until relaunched: `hooks.json` embeds the digest path.

**Roster.** 293 agents; `service-operations-engineer` and `monitoring-engineer`
are packaged contractors with the `operations` domain. On the full roster six of
eight operational work statements rank them first; the distribution-url phrasing
is top-three behind `tool-evaluator`. The monitoring engineer covers
`implementation` and `release` on a copy of the live store after install.

**AR-397 (new, `in_progress`).** A packaged contract revised at the current
template had no predecessor, so `agency install` would preserve a live worker
forever. Superseded definitions are kept verbatim, pinned by prompt hash,
returned as predecessors and as metadata authorities, and every pin is checked
before the identity pass. Lifecycle phases are not identity; `hosts`,
`platforms` and the two scenarios reach routing metadata but not the prompt;
installer per-slug tables remain the open case.

**Tracker.** Issues #641 to #654 map AR-384 to AR-397; twelve `done` records
have closed issues; #537 and #581 closed. `verify_tracker.py` names none of
them. The older rows reading `pending authorization` were not authorized.

**Review process.** One Opus reviewer per checkpoint, never a fork, never a
fan-out: `~/.claude/agents/adversarial-reviewer.md` (`model: opus`,
`effort: max`; visible after a claude restart). Two runs today: #638 after
merge (false-green fixture, stale figures, unreachable pin) and #640 before
merge (removed hook was needed, pin could not trip on a current machine,
mechanism load-bearing for the live hire case). Each cost about 200k Opus tokens.

## completed-evidence

Commits on `main`: `e2b149e2` contracts, `ea2efe29` follow-up, `dda2c8a3` and
`f67b718f` AR-397, `a587fcce` tracker mappings. Live proofs: pointers and empty
drift list above; store copies show 293 agents, 28 from `agency-runtime`, the
monitoring recruiter row `("implementation", "release")`, no divergence, hire
case auditable. Planner replay by deployment id with `cache: {"no-cache": true}`:
gpt-5.5 (`c2692490`, order 1) JSON 20 of 20 across four prompt shapes;
glm-5-turbo (`ed1b5bbc`, order 2) 0 of 5 plan calls, every one a 45 s gateway
timeout, 2 of 2 on the small subject call. Route by id: `"model": "<model_info.id>"`.

## exact-blocker

**Staffing ends at inference.** 156 receipts since the last declaring one, 136
of them `routing:workforce_provider_unavailable`; this session's own turns read
`inference_unavailable`, `staffing_critic_rejected`, `roster_coverage_gap`,
`inference_invalid`. Until a turn is staffed: AR-393 c5 stays unmeasurable
(zero declaring receipts after the fix), AR-370 c1's live half is unproven, and
the one open design question, whether a real planner labels "install this:
url" as `operations` or `platform`, has no data. The prose planner replies from
the afternoon did not reproduce; their prompts are not stored.

## same-task-continuity

1. The install drift line names no host; read `cli_install_drift_reports()`
   per host, the pointer, and the launcher tree under
   `runtime-sha256-<digest>/site-packages/agency_runtime`. Relaunch to use it.
2. Lifecycle phases travel through the repair pass; prose changes need the
   superseded mechanism; a change to `_DOMAINS`/`_ARTIFACTS`/`_OPTIONAL_TOOLS`
   is still not covered. Re-pin the recruiter envelope last, with a dated note.
3. A fixture of only the 17 packaged contractors ranks them first trivially;
   score retrieval against the full packaged roster.
4. The classifier blocks one command that bundles push, `gh pr create` and
   `gh pr merge`; push and create together, merge alone, and retry the merge,
   which races GitHub's mergeability right after a push.
5. Compare any failing test against `origin/main` before blaming a branch;
   `test_dashboard...revision_bound_lifecycle` was fixed in #639.
6. The repo's stale `build/` directory is why every venv carries the retired
   `domain_expansion.py`; clear it before the next venv build.
7. One heredoc per shell call, printf commit messages to a file, `&&` after
   every gate, and never pipe a gate through `tail`.

## next-bounded-work-package

1. Owner: relaunch claude with the env sourced under `set -a`; open a fresh
   `codex` TUI and choose `Trust all and continue`, then
   `agency install --agent codex --verify-activation` with the key.
2. Capture one real "install this: <url>" turn once staffing works; decide
   `platform` from what the planner writes, not by adding it.
3. AR-397: close through the AR-361 flow (acceptance record, isolated verifier)
   and decide the per-slug table case.
4. AR-393 c5 on the first staffed turn that declares a gap; store copy only.
5. Operator decision: glm-5-turbo cannot serve a plan call inside its 45 s
   deployment timeout, so the planner alias has one working deployment.
6. Clear `build/`, then rebuild the venv at the next merge and reinstall.
7. Ask before creating issues for the older `pending authorization` rows.

## verification

Per PR: #638 116 tests on its neighbourhood, #639 116, #640 431 across fourteen
suites, all green except the pre-existing failures also present on `main`;
ruff clean on every changed file (the repository baseline is not clean);
`verify_docs`, `docs_metadata`, `update_worklog --check` and the policy gate
green on every branch; two Opus reviews with every finding either fixed or
recorded as an open decision.

## constraints

- `agency.yaml` is operator configuration; timeouts sit at 60000 with the
  dated backup. Deployment order and `workforce.mode` were not touched.
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; measure on copies. Live host
  invocations need `common.env` sourced under `set -a`; `agency install` runs
  without the key.
- Review passes: exactly one reviewer, pinned to Opus, artifacts only.
