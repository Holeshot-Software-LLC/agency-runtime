---
title: "AR-404 Hermes and OpenClaw native verification"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-08
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
branch: codex/ar404-hermes-openclaw-20260908
evidence_commit: 1dd69c3ad1e1c86db386dff69cd8a96ee8dc41ac
minimum_ledger_commit: 70ba71d8f92a3f5bb536d5ec32ab34232d803b4c
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 Hermes and OpenClaw native verification

## Checkpoint

Owner approved refreshing Hermes and OpenClaw and testing one ordinary native
turn each. OpenClaw gateway stop/update/restart is included in that approval.
Baseline clean main24b50cb8. Hermes native attempt failed after accepted staffing/injection (AR-418/#796).
OpenClaw refreshed, gateway restored RPC-green; native turn returned correct
headers but left Agency active with zero finalization (AR-419/#797).
Bounded verification is complete with negative full-roundtrip verdicts.
No native success claim yet. AR-404 stays open; AR-414/415 are acceptance-closed.

## Completed evidence

Codex fresh turn proved staffing, exact specialist injection, five headers and
Stop acceptance in56.656s. All seven isolated AR-414/415 verdicts satisfied;
merged PR793/794. This is not other-host proof.
Installed source8629e2ed wheel matches all614package files. Both other hosts
had old projection4d2934ddb59e versus installed6e7dc299c23e, enabled/runtime
unverified and absent attestation. Hermes refresh now succeeds with backup
20260908T195311.634794Z and bundlebdce2726fd10. Existing Hermes processes untouched.

## Exact blocker

No external gate blocks the approved work. Hermes returned an output-limit error after accepted staffing and full card
injection; no finalization or five-line header. OpenClaw has truthful headers but no finalization or exact card proof. Their old
failure records are preserved, not treated as current-artifact results.

## Same-task continuity

Read the linked Hermes/OpenClaw worklog. Work only in the named owned branch.
At or below50percent remaining, commit the smallest safe evidence/ledger pair
and continue in the same task. Preserve unrelated worktrees and operator files.

## Next bounded work package

Repair the exact Hermes output-limit lifecycle under AR-418 and OpenClaw
ordinary CLI terminal handoff under AR-419. Capture supported native context
evidence before claiming exact OpenClaw card delivery. Do not repeat either
trial merely for approval; preserve validators and inference-owned staffing.

## Verification

Fresh host-focused254pass/1skip, production1151pass/3skip, UI224pass,
Ruff/routing/docs/tracker pass and frozen conformance188/188 with source unchanged.
No exhaustive suite, Windows matrix or all-host release certification.

## Constraints

No manual specialist selection, trust bypass, weaker validator or critic,
unbounded retries, credential replacement, unrelated backlog work or false
finalization. Preserve normal gateway service restoration and exact PR ledgers.
