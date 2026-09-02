---
title: "AR-356 research-lifts implementation and backlog-triage capsule"
status: active
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [handoff, research-lifts, triage, reliability, fail-open]
related:
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/roadmap/issue-AR-360-battery-pass-k-grading.md
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
  - docs/roadmap/issue-AR-362-agent-chaos-harness-oracles.md
  - docs/roadmap/issue-AR-363-deployed-fix-witness-manifests.md
  - docs/roadmap/issue-AR-364-audit-external-review-cards.md
  - docs/roadmap/issue-AR-365-hermes-fail-open-gate-trace-resolution.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-367-fail-open-resident-binding-claim.md
  - docs/roadmap/acceptance/README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-356
branch: main
evidence_commit: c39e1ccf2b7ad579d31ce3fbc704e18bcc80c8e4
minimum_ledger_commit: 5e5f9dac9132acac3ceecf9503482f706f09a757
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
---

# AR-356 research-lifts implementation and backlog-triage capsule

Start-here capsule for a fresh session, anchored on AR-356 as the head of
the owner-approved queue. Owner scope (2026-09-01): implement the ten
research lifts and disposition the open backlog per the triage below; the
verification section is the owner-set definition of done. Standing rules:
attack every finding before reporting it; findings go in repo docs, not the
reply; prove gates locally (Actions is off); ledger dance on every change;
end every turn with exactly one question; no subagents on this account.

## checkpoint

Main is green on both strict gates at `5e5f9dac` (2026-09-02 ~05:00Z). The
runtime deployed on this box is still the 2026-09-01 night build
(`6ba65aa9`, projection carrying kernel v5 + AR-346/365/366); nothing from
this session is deployed yet. Merged since the previous capsule, each with
its ledger row: AR-356 (#452, #462), AR-352+AR-360 (#451), AR-363 (#453),
AR-361 (#457, #459, #460), AR-367 (#465, new p1 defect found live), AR-359+
AR-354 (#467), AR-353+AR-355 (#469), AR-362 (#473), plus the per-host policy
proof (#471) and the AR-355 close (#475).

Done with isolated verdicts (AR-361 records under
`docs/roadmap/acceptance/`): AR-352, AR-355, AR-356, AR-360, AR-361,
AR-362, AR-363. In progress: AR-353 (Linux measured; Windows half open),
AR-354 (criterion 2 satisfied; criterion 1 waits on a re-verification
against a candidate that carries the regenerated pytest evidence file),
AR-359 (live policy re-set is a deploy step), AR-367 (live box after
deploy), AR-365/AR-366 (live boxes).

Live receipts this session: AR-365 observed — `hermes -z` turn 946
(2026-09-01 23:01:57Z, trace `…:866e938b`) closed `preflight_failed` and the
full draft was delivered, no block message. AR-366 not yet observed: three
openclaw probes all staffed. The AR-353 window measured on this box:
273 turns / 69.2% fail-open in 24 h (84.4% in the last 6 h), dominated by the
recruiter rejecting its own structured output (`staff_without_safe_team`
×408, `invalid_candidate` ×166); see `agency evidence staffing`.

## completed-evidence

- Ten-lift status: AR-360 done, AR-361 done (the gate is live: every done
  flip needs a record with isolated codex verdicts; grandfather list frozen
  at AR-346), AR-362 done (both experiments pass live, receipts under
  `~/.agency-runtime/evidence/chaos/`), AR-363 done (witness manifests;
  claude wiring measured, other hosts attest their pointer), AR-364 open
  (worktree has a partial multi-source schema in `roster/bundled.py` only).
  Scope notes: AR-356 done incl. tool degradation; AR-355 token cost
  measured (~325 tokens per ready turn); AR-357 open (worktree carries
  `header/response_contract.py` + partial contract/finalize edits); AR-336/
  AR-120 routing-eval notes untouched; AR-266 unchanged.
- Fail-open family: AR-367 fixed and merged (fail-open turns now claim and
  acknowledge the resident binding; next turn plans `reused`); lifecycle
  suite green; `test_coverage_final_host_cli.py` and
  `test_resident_manager_lifecycle.py` joined the fast spine.
- Measurement tools shipped: `agency evidence staffing`, `agency evidence
  context-budget`, `agency evidence witness`, `agency chaos run`,
  `agency battery --trials`.

## exact-blocker

None mechanical. AR-354 criterion 1 needs one more re-verification after
the regenerated evidence file is on main (its candidate must contain the
file). AR-366's live box still needs one real fail-open openclaw turn.

## same-task-continuity

Continue on `main`; one branch per package in its own worktree under the
session scratchpad (`wt-ar357`, `wt-ar358`, `wt-ar364` hold partial work,
uncommitted). Feature PR (single commit) rebase-merged, then a
`docs(worklog):` tick PR with the post-merge SHA; done flips land in a
follow-up docs PR carrying the acceptance record (a commit cannot cite its
own SHA). Verifier runs use `--provider codex` to spare the Claude window.
Clear stale `tests/__pycache__` after same-length constant edits.

## next-bounded-work-package

1. AR-354 final re-verification and done flip (candidate = the merge of the
   regenerated evidence file); then AR-364 (path A: multi-source audit
   pipeline; clone msitarzewski/agency-agents at `459dce83`, ECC cards at
   `ca185ef5`, MIT), AR-357 (finish contract delivery in hooks/bridges +
   tests), AR-358 (doctor `--fix-perms`, tests), then the AR-336/AR-120
   scope notes.
2. Gates + all four batteries (`agency battery --force --trials 2`), then
   deploy per AR-337 (venv pip-reinstall of the exact SHA with
   `--no-deps --force-reinstall --no-cache-dir`, `agency install` + per
   agent incl. the AR-358 openclaw consent, codex tmux re-trust, hermes
   single-process restart, openclaw gateway stop/install/start), re-set the
   live operator policy with its five lines (AR-359), batteries, baseline.
3. Live verification: herdr tabs for every host CLI (headers, staffing,
   hiring), the Telegram bots nexus (openclaw) and mentor (hermes), the
   AR-356 disclosure line and AR-367 `delivery=reused` on a fail-open
   claude turn, AR-366 on openclaw.
4. Triage closes with receipts (list below), tracker closes for every done
   item, registry statuses, and main green on both strict gates.

Backlog triage — owner-directed dispositions (verify before closing, cite
receipts in every close): close with evidence AR-347 #404, AR-337 #362,
AR-298 #336, AR-265 #317 (finish or waive the last box), AR-127 #151
(parked until zcode exists, owner sign-off), AR-119 #132 (superseded by the
inference-first system; file a residual). Verify-then-close-or-finish:
AR-199 #161 (re-verify open boxes on live codex turns), AR-344 #399 (the
codex Stop gap is fixed by AR-366 — close after a live fail-open codex turn),
AR-261 #309 / AR-262 #311 / AR-264 #313, AR-115 #127 (overlaps AR-357).
Keep open: AR-266 #320, AR-335 #350, AR-336 #353, AR-200/201/207/208/209,
AR-235/236/250/251, AR-125 #138, AR-178 #153, AR-348..351, AR-353, AR-367.

## verification

Owner-set definition of done for this goal (2026-09-01):

1. All ten lifts implemented with regression tests (AR-360..364 complete;
   scope notes on AR-120/266/336/355/356/357 honored), plus AR-356 and the
   AR-365/AR-366 live boxes.
2. Every change proves the local gates: focused tests, the named fast Python
   spine (`-W error`), ruff check+format (binary under
   `~/.cache/agency-runtime-ar281-trusted-venv/bin/`), both docs gates, the
   worklog dance; routing + decision-conformance evals whenever routing or
   policy surfaces changed (copies-venv + umask 077).
3. All four harness batteries pass on this machine.
4. Only if all pass: deploy to every harness here per AR-337, then smoke
   test each host directly with a live turn.
5. Then verify end to end, unattended, with receipts: herdr tabs for every
   host CLI (Agency header lines, staffing selection, hiring), and the
   Telegram bots nexus (openclaw) and mentor (hermes), confirming replies
   deliver with the same evidence.
6. Finish honest: registry statuses flipped with receipts, the triage closes
   executed, and main green on both strict tracker gates.

## constraints

- GitHub Actions is off — never claim CI ran; prove gates locally.
- The pre-tracker allow-list is frozen (AR-227/228 PR-tracked); new docs
  always carry `tracker_url`; done flips need an AR-361 record.
- Never name the legacy sibling repository in roadmap docs. sqlite3 CLI is
  absent (python3 module); bare foreground `sleep` is blocked.
- No subagents or forked skills on this account (they burned the usage
  window); work sequentially, one worktree at a time.
- Findings in repo docs; one question per turn; Rule 8 always.
