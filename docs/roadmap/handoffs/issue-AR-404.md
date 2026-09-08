---
title: "AR-404 Hermes and OpenClaw native verification"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-08
tags: [handoff, codex, launch, live-evaluation]
related:
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
evidence_commit: 013ab75f66c5c3ce1e147e9fd8794c2ea32aa168
minimum_ledger_commit: df45b6cb19b4b3dd4221d9892cd40d32d194b2df
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 Hermes and OpenClaw native verification

## Checkpoint

Owner approved refreshing Hermes and OpenClaw and testing one ordinary native
turn each. OpenClaw gateway stop/update/restart is included in that approval.
Baseline clean main24b50cb8. Hermes installer succeeded; package is demo_ready.
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

No external gate blocks the approved work. Fresh native staffing, injection,
headers and finalization are still unproved for Hermes and OpenClaw. Their old
failure records are preserved, not treated as current-artifact results.

## Same-task continuity

Read the linked Hermes/OpenClaw worklog. Work only in the named owned branch.
At or below50percent remaining, commit the smallest safe evidence/ledger pair
and continue in the same task. Preserve unrelated worktrees and operator files.

## Next bounded work package

Run Hermes from a fresh normal CLI process. Then stop the OpenClaw gateway,
refresh through the normal installer, restore its service and test one ordinary
turn. Correlate each host's own receipt and native output. Diagnose any failure
before a further attempt; preserve all validators and inference-owned staffing.

## Verification

Unchanged source has focused108pass, production1151pass/3skip, UI224pass,
Ruff/routing/docs/tracker pass and frozen conformance188/188 with source unchanged.
No exhaustive suite, Windows matrix or all-host release certification.

## Constraints

No manual specialist selection, trust bypass, weaker validator or critic,
unbounded retries, credential replacement, unrelated backlog work or false
finalization. Preserve normal gateway service restoration and exact PR ledgers.
