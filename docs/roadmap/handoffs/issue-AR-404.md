---
title: "AR-404 native terminal repairs and remaining gates"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-09
tags: [handoff, hermes, openclaw, live-evaluation]
related:
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/worklog/2026-09-08-hermes-openclaw-native-refresh.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-codex-roundtrip-20260908.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/worklog/2026-09-08-codex-launch-roundtrip.md
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/worklog/2026-09-08-fresh-codex-activation.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar423-native-priority-20260909
evidence_commit: 5dbe612a7dd3bd7ecca1b2f60411a44b175d278f
minimum_ledger_commit: adab07907448c152e5a214e8abd5150d535f282d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 five-host reliability

## Checkpoint

Owner order: OpenClaw, Hermes, Codex, Claude. Zcode changes are deferred but its
historical failures remain in the five-host scope. AR-428 planning repair merged
in PR831 (`0839e158`) and closed. AR-423 now has all three isolated criteria
satisfied; PR832 carries fresh complete-team native evidence and the PR831 ledger.
AR-404 and AR-418 remain open; no all-host reliability claim.

## Completed evidence

OpenClaw review/follow-up sessions under
`agent:openclaw:ar404-20260909-priority-review-followup` passed five Store headers
and authoritative hashes in82.956s/58.928s. Only the review critic packet was
captured; no llm_input observation proves new full-card injection. No repair was
inferred from the unreproduced old veto. Final gateway RPC healthy; observers removed.

AR-428 source `0ac9d78e`, artifact `ecf8a584`, recipe20 distinguishes unexecuted
proposed-test review from observed results. Exact616 installed package files match.
Hermes and Claude refreshed; Codex/OpenClaw/Zcode retain their prior projections.
All three AR-428 planning criteria satisfied; both current Hermes staffing failures
remain authoritative and no terminal completion is claimed for them.

Codex8/8 hooks trusted, current hashes equal prior native proof, all651 files in
published projection `37c1bf7d5eb0` match. Prior fresh native session
`01a0877b-45dd-7b01-b99d-92c03587393f` passed five cards/headers/finalization in103.434s.
This parent remains stale on `6db15efbecbe`; reinstall cannot refresh it.

Claude session `a5c13def-36a1-4a3e-9484-d0f09f105209`, trace
`95f96215-d84b-4b4e-9628-c808e99b9d23`, passed4/4 inferred full native MCP cards,
five Store headers and authoritative hash
`1c5f87780ecf485d2f4ab4018b3a71a45c79522edd237707447667cfca638c1c`
in264.750s. Distinct correctness/security bindings and no staffing advisories;
no delegated specialist execution claim. Isolated verdicts7371e07f/de031b6f/0e4e187d
satisfy AR-423. Two exact Allow rules unchanged; published79138e80 has651 matching files.

## Exact blocker

Hermes sessions `20260909_153129_1f3091` and `20260909_153433_eef6b8` failed
wrong-neighbor staffing in81.860s/78.821s. The second exact critic packet is
`AR-428-observed-native-critic-packet-20260909.json`: four units, no test-evidence,
independent static review; type-design and silent-failure nominees remain. The
critic code does not establish a sole cause. Neither receipt has finalization.

AR-418 upstream PR106490 remains OPEN at30f421ecce. Actual Hermes checkout is
clean7cd91114b462b7af76e558cc4e97f82201d2e884. Default adoption and the original
truncation cap are unproven. Zcode's early invalid finalizations remain failed;
later headers cannot reopen or replace them. Old sample8/15 remains historical.

## Same-task continuity

After PR832 merge, use a fresh owned worktree. Preserve unrelated scratchpad and
Windows work. At or below50percent checkpoint substantive state plus exact ledger
and continue. No empty recovery commits, forced transfer, or failed-receipt reopening.

## Next bounded work package

Inspect Hermes's observed nomination packet against selected contracts and eligible neighbours. Choose a
bounded repair only from that evidence; do not assume a critic mistake. Preserve
the separate AR-418 upstream terminal gate. Keep the owner's host order and Zcode deferral.

## Verification

Recipe20 focused164/1skip; named production1151/3skip; UI224; routing; Ruff788;
frozen conformance188/188; canonical artifact/Twine/installed smoke passed.
Claude context12 passed. Final documentation, worklog and tracker checks precede
handoff. No exhaustive or Windows workflow ran.

## Constraints

Inference alone selects specialists. Preserve independent critic, validators,
trust, native limits and caller scope. No manual selection, acceptance, external
messages or unbounded retries. No pending Codex trust or Claude tool approval.
AR-419/423/425/426/427/428 have satisfied their scoped acceptance gates; umbrella AR-404 stays open.
