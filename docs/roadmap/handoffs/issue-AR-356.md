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
  - docs/roadmap/issue-AR-368-normalize-trust-chains-before-executing-probes.md
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
  - docs/roadmap/issue-AR-366-openclaw-fail-open-withhold.md
  - docs/roadmap/acceptance/README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-356
branch: main
evidence_commit: f9321bdde6bf8dc2e07dae5009d3bdb525259c0f
minimum_ledger_commit: 48881d1d6af3363941b752753ece264d4b6a3dad
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

Main is green on both strict gates at `f9321bdd` (2026-09-02 ~12:35Z) and the
runtime deployed on this box is that same SHA: venv pip-reinstalled with
`--no-deps --force-reinstall --no-cache-dir`, all four host plugins
reinstalled, hermes dashboard restarted, openclaw gateway stopped/installed
with `--accept-capabilities`/started.

All ten research lifts are now implemented. Closed this session with
acceptance records and isolated codex verdicts, tracker issues closed:
AR-364 (#482, #483, #484, #485, #486, #487), AR-357 (#488..#492), AR-358
(#494 and its follow-ups). Merged earlier in the goal: AR-352, AR-353,
AR-355, AR-356, AR-359, AR-360, AR-361, AR-362, AR-363, AR-367.

Three defects were found *by* the deploy and fixed in it, all AR-368
(#500): Claude Code rewrites its own npm tree group-writable on every
invocation, so AR-358's install-time repair is undone by the next probe
(chains are now normalized immediately before any executing probe, opt-in so
`status`/`doctor` stay read-only); `~/.claude/projects` is now a registered
chain, because the canary proves a delivered child card by reading those
transcripts; and the claude marketplace registration normalized *after* the
inventory probes that launch the host. Two doctor tests that were failing on
main -- they let `run_doctor` read this machine's battery outcomes -- were
isolated.

## completed-evidence

- Ten-lift status: AR-360, AR-361, AR-362, AR-363 done; AR-364 done (path A,
  multi-source audit pipeline, schema-3 manifest, ECC cards pinned at
  `ca185ef5`, roster 263 -> 265); AR-356 done incl. tool degradation; AR-355
  measured; AR-357 done; scope notes on AR-120/AR-266/AR-336 recorded and
  unchanged.
- Batteries on the deployed build: hermes and openclaw pass (openclaw passes
  both trials); codex reports `attended_trust_required`; claude fails its
  canary. Both remaining failures are attended, not code: codex needs a fresh
  terminal TUI with "Trust all and continue", and claude's live canary now
  reaches the invocation (the two permission blockers are gone) but reports
  `host invocation did not complete successfully` and
  `multiple_child_artifacts`.
- Live AR-358 receipts: `agency doctor --fix-perms` repaired 29 entries under
  the Agency marketplaces chain; the openclaw install carried
  `--accept-capabilities` on both install and enable and came back
  `loaded=True enabled=True`.

## exact-blocker

The hermes withhold is destroying real answers and needs an owner decision,
written up under "Open owner decision" in
`docs/roadmap/issue-AR-366-openclaw-fail-open-withhold.md`: the mentor bot's
ready turns close `response_invalid` with all five header lines missing
(13 such turns against 5 completed in 24 h), so `transform_llm_output`
replaces the whole reply. The obvious repair was implemented and backed out
because it hid an open delegation. Three options are recorded; option 2
needs the delegation guard widened beyond `strongly_preferred` first.

## same-task-continuity

Continue on `main`; one branch per package in its own worktree under the
session scratchpad. Feature PR (single commit) rebase-merged, then a
`docs(worklog):` tick PR with the post-merge SHA; done flips land in a
follow-up docs PR carrying the AR-361 acceptance record. Verifier runs use
`--provider codex`. The local spine cannot run under the trusted ruff venv
(not an OS-protected interpreter, exit 4); run ruff from
`~/.cache/agency-runtime-ar281-trusted-venv/bin/` and pytest with the system
`python3` over `WORKFLOW_CONTRACTS + PRODUCTION_SPINE`.

## next-bounded-work-package

1. The hermes owner decision above, then implement whichever option is
   chosen with the delegation guard it needs.
2. Finish the claude canary: `host invocation did not complete successfully`
   and `multiple_child_artifacts` are no longer permission defects and need
   their own diagnosis; then `agency battery --force --trials 2` and
   `agency battery --baseline`.
3. Attended: open a fresh terminal, run `codex`, choose "Trust all and
   continue" for all 8 Agency hook events, then re-run the codex battery.
4. Live verification still open: herdr tabs for every host CLI (headers,
   staffing, hiring) and the Telegram bots nexus (openclaw) and mentor
   (hermes) end to end.
5. Triage closes with receipts (list below), and AR-368's remaining box.

Backlog triage -- owner-directed dispositions (verify before closing, cite
receipts in every close): close with evidence AR-347 #404, AR-337 #362,
AR-298 #336, AR-265 #317 (finish or waive the last box), AR-127 #151
(parked until zcode exists, owner sign-off), AR-119 #132 (superseded by the
inference-first system; file a residual). Verify-then-close-or-finish:
AR-199 #161 (re-verify open boxes on live codex turns), AR-344 #399 (the
codex Stop gap is fixed by AR-366 -- close after a live fail-open codex turn),
AR-261 #309 / AR-262 #311 / AR-264 #313, AR-115 #127. Keep open: AR-266 #320,
AR-335 #350, AR-336 #353, AR-200/201/207/208/209, AR-235/236/250/251,
AR-125 #138, AR-178 #153, AR-348..351, AR-353, AR-366, AR-367, AR-368.

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
