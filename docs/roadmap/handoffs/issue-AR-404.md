---
title: "AR-404 native terminal repairs and remaining gates"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-10
tags: [handoff, hermes, openclaw, live-evaluation]
related:
  - docs/worklog/2026-09-10-hermes-assurance-investigation.md
  - docs/roadmap/issue-AR-431-preserve-keep-going-task-context.md
  - docs/worklog/2026-09-09-ar429-merged-checkpoint.md
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
branch: codex/ar404-hermes-assurance-20260910
evidence_commit: 2a5663152f6a6c916596fa92b5c7ba8c902b5745
minimum_ledger_commit: 4544efd67074be9939aaf56e448ac1de189f2bcb
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 five-host reliability

## Checkpoint

September10 demo_ready: exact ordinary-review critic correctness is
indeterminate because the failed trace retained no plan/proposal/critic packet.
Fresh parent MCP succeeds. Focused17, production1151/3skip, UI224, routing,
Ruff788 and docs pass; private conformance188/188 passed. One native diagnostic pending.
No product repair or historical receipt mutation. See current worklog.

AR-431/#839 source05653bc9/artifactf95e0ab6 has current8/8 Codex trust and fresh
native initial/keep-going receipts01a08b18-1a43/01a08b1a-f50d. Full cards4/5,
five headers and authoritative hashes40bace52/5c36ceba match. Context correlates
to the exact completed review with fresh inference and no replay. PR842 carries
the evidence; all three isolated criteria satisfied on the first pass. Reranker-invalid and recruiter-timeout
degradations remain visible despite successful configured fallback and critic.

Owner order remains OpenClaw, Hermes, Codex, Claude; Zcode changes are deferred,
with its historical failures still in the five-host scope. AR-429/#834 merged
in PR836 at82090e11 and closed after one native pass and all three first-pass
isolated verdicts. AR-423/#811 and AR-428/#826 are also closed. AR-404/#672,
AR-418/#796 and deferred fixture maintenance AR-430/#835 remain open.

## Completed evidence

AR-429 sourcef6d58d5a, artifact47241e5e, recipe21 ground required specialties in
actual unit scope while preserving inference selection and the independent critic.
All616 installed package files match wheel41a6e9e76daa3da165ba03b9e933c2f71ccfe54a64d116fff5cc8bf842ebafe0.
At that checkpoint only Hermes refreshed for recipe21. Claude retains recipe20;
OpenClaw/Zcode retain their prior projections. Codex now has AR-431 recipe22.

Hermes session20260909_213316_5f974b, trace
20260909_213316_5f974b:011accaf-7dba-4413-b99c-fbbb8508459b:bb0af9fd completed in
111.388s. Inferred team code-reviewer/python-application-engineer/software-test-engineer:
three full native cards, five Store headers and authoritative final hash
372378a52de65f298cb822d3313cea5205bf466e6fb80239b1b19a68bd49d5fe match. Actual
recruiter prompt has the recipe21 prefix; critic approved; four units retain
independent static review. Two stage packets captured, observer config restored
byte-for-byte. Isolated091e5a21/bcce1a9a/bc0261d5 all satisfied atcandidate0d89987d.
No delegated specialist execution or test-execution claim.

Prior OpenClaw review/follow-up under
agent:openclaw:ar404-20260909-priority-review-followup passed headers and final
hashes in82.956s/58.928s. Full-card injection was unobserved. Final gateway RPC
healthy, PID2680971, no restarts or active observer.

Before AR-431 refresh, Codex8/8 trust and651 published37c1bf7d5eb0 files matched.
Prior fresh session01a0877b-45dd-7b01-b99d-92c03587393f passed five cards/headers/
finalization in103.434s. This long-lived parent remains stale6db15efbecbe;
reinstallation cannot refresh it or establish a new native-process claim.

Claude sessiona5c13def-36a1-4a3e-9484-d0f09f105209, trace95f96215-d84b-4b4e-9628-c808e99b9d23,
passed four native MCP cards, five headers and authoritative1c5f8778 final hash
in264.750s. AR-423 isolated7371e07f/de031b6f/0e4e187d satisfied. Two exact Allow
rules unchanged; prior79138e80 projection had651 matching files.

## Exact blocker

Remaining original Hermes ordinary_review session20260909_113727_2e00b0, trace
20260909_113727_2e00b0:6c87a1d6-a92a-493a-9f11-7c1b27e84a58:e03a9447 failed with
staffing_critic_rejected and critic_missing_independent_review_assurance. Read-only
audit found zero routing/intent/selected-card/finalization/model rows, empty
preflight_result and no raw critic packet. The veto alone cannot establish a
critic bug. Historical assurance correctness remains indeterminate.
Source: AR-404-hermes-suite-after-planner-context-20260909.json. The historical
follow-up and multi-step invalid receipts omitted all five headers and stay failed.

AR-418 upstream PR106490 is still OPEN at30f421ecce28c563a62a97cc227c800954ff9b3b.
Actual Hermes checkout is clean7cd91114b462b7af76e558cc4e97f82201d2e884. Default
adoption and original truncation-cap acceptance remain unproven. Zcode's early
invalid finalizations cannot be repaired by later headers. Original fixedsample8/15
remains historical; the new scoped demos are not a replacement all-host sample.

## Same-task continuity

Completed implementation branches/worktrees are historical after merge. Start
new implementation in a fresh owned worktree from updated origin/main. This
checkpoint branch owns records only. Preserve unrelated scratchpad and Windows
work. At or below50percent checkpoint the smallest safe substantive/ledger pair
and continue; never reopen a failed receipt or create an empty recovery pair.

## Next bounded work package

All pre-demo checks pass. Run one fresh exact-request
Hermes ordinary-review diagnostic with bounded recruiter/critic packet capture.
Judge only its own plan/contracts and terminal evidence; do not relabel the old
veto. AR-418 upstream remains OPEN at30f421ecce and installed native checkout
clean7cd91114; adoption and original cap remain separate. Preserve owner order.

## Verification

Recipe21 focused217/1skip, named production1151/3skip, UI224, routing, Ruff788,
frozen conformance188/188 and canonical build/Twine/installed smoke passed.
Broader optional focused240/1skip has2 unchanged-main failures, filed AR-430;
no product change was made to satisfy stale domain-coverage fixtures. Docs,
worklog and strict tracker parity are required after merged record maintenance.
No exhaustive or Windows workflow ran; no all-host reliability claim.

## Constraints

Shared staffing and inference-only selection. Preserve independent critic,
validators, trust, native limits and caller scope. No manual selection, acceptance,
external messages or unbounded retries. AR-431 Codex hook trust is confirmed8/8;
Claude tool approval remains complete. Necessary Hermes/OpenClaw refresh and normal maintenance remain authorized.
