---
title: "AR-404 native terminal repairs and remaining gates"
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
branch: codex/ar404-native-recovery-20260908
evidence_commit: 9418ab834cbba26dd91c4d5de7a14e9f80c7ceb4
minimum_ledger_commit: 1106cf736bb2809a83695290c84f95f39f60300d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native terminal repairs and remaining gates

## Checkpoint

PR799 merged at58247849. Repair/evidence branch is historical. This recovery
branch records the merged checkpoint; if merged, create a new owned worktree.
Installed immutable source8921c77e contains OpenClaw repair94b9eb28 and
Hermes adapteref7a0466; all614
package files match its verified wheel. OpenClaw and Claude now have fresh
ordinary accepted terminal evidence. AR-404/418/419 remain open; no all-host
completion. AR-414/415 remain acceptance-closed. Windows work is untouched.

## Completed evidence

OpenClaw traceb2f9ef9e-1280-4c28-9934-6b094bdfcf6a: accepted staffing,
truthful headers, one authoritative accept, exact visible-response SHA256
81356a9c914b08463d76681650c7daf4ae24ad6d4236a880dff15df54066c466,
completed Store state,195.996s total/159.779s staffing. Normal gateway
maintenance restored RPC health and unchanged configuration sections. No delivery.
See evidence/AR-419-openclaw-terminal-20260908.json. Exact injection is unproven.

Claude trace16079749-cfc9-4d90-b4d4-6f6ce8104eec: full selected card in
native rendered hook context, truthful headers, accepted exact response hash,
completed Store,63.879s total/43.063s staffing. Two owned executable parent
directories tightened775to755, normal refresh, native2.1.265. See
 evidence/AR-404-claude-native-20260908.json. No permission bypass.

Zcode desktop3.10.2 includes native CLI0.16.5. Installed an unchanged copy of
its bundled zcode.cjs and a PATH launcher; native doctor passes. Normal Agency
refresh succeeds. Native build-mode trial reaches missing answering-model configuration; CLI
config has only hooks, desktop uses separate Z.AI OAuth. Provider choice asked
once. This is executable proof only.

## Exact blocker

Hermes native candidate59e52e556a is preserved as a repository patch;34native
tests and94adapter tests pass. Candidate-source session20260908_172942_b70b9d passes exact card/headers/accept
in194.347s. Normal native checkout is unchanged; upstream PR consent asked once.
See evidence/AR-418-hermes-candidate-native-20260908.json. Original
Hermes output-limit early returns bypass native finalizer/session-end callbacks;
outer runner and CLI can misclassify printable partial output as success. No
supported terminal-result hook covers those returns. AR-418 needs native-boundary
repair, not fabricated adapter success. Original provider cause/token cap unproven.
OpenClaw exact injection observer requires native capability consent, asked once;
no observer was installed. Do not treat elapsed time as approval.

## Same-task continuity

Read the linked native-refresh worklog and2026-09-08-native-terminal-repair.md.
The branch field is provenance; recheck merge state and use a new owned branch
for subsequent changes.
At or below50percent remaining, checkpoint the smallest safe evidence/ledger
pair and continue. Preserve unrelated worktrees and operator files.

## Next bounded work package

Staffing reliability is the immediate priority after repeated owner-visible
failures. AR-420 captures a reranker cross-unit candidate defect and a bounded
schema repair, installed source3fe3d7ba/all614wheel files verified; focused164,
production1151/three skips, UI224pass. Fresh native Codex41.514s completed with
all staffing stages applied, full card injection and matching accepted response
hash; trace01a0831f-1a40-7a12-a079-3386a3b439d3. Isolated acceptance pending.
Owned branchcodex/ar420-staffing-reliability-20260908, PR803.
Latest native trace01a0830f-8143-7542-ac77-5ace98ceb5d4 remains failed with
critic_wrong_neighbor_selection; its proposal is unavailable, veto unadjudicated.
See2026-09-08-reranker-membership-repair.md. Preserve independent critic and
validators; one accepted turn never establishes general reliability.

Waiting for owner choices: standalone Zcode answering provider, native OpenClaw
observer consent, and permission to submit the tested Hermes patch upstream.
Then finish the three remaining gates without retries or trust bypass. Hermes
candidate-source success is proven; default native adoption remains. Close issues
only after isolated acceptance. Preserve the completed PR799 merge and exact ledger.

## Verification

Latest focused94passed; native Hermes34passed; production1151passed/3skipped; UI224;
Ruff/docs/metadata/routing pass. Current8921c77e frozen conformance188/188 passes,
source unchanged, after private umask077 correction. No exhaustive dispatch,
Windows matrix or all-host certification. Prior Codex56.656s roundtrip is historical
comparison evidence; current Codex preflight failed and is honestly unstaffed.
Exact prior handoff receipt preserves critic_wrong_neighbor_selection; no transport
recurrence or erroneous veto is inferred. Fresh native Codex process01a082f1-0e89-7f51-b4e7-7fb28b69917e
remains unproven: status exposes no hash and bwrap prevents wiring command;
no trust/sandbox bypass. See evidence/AR-404-codex-freshness-20260908.json.

## Constraints

No manual specialist selection, trust bypass, weaker validator/critic, unbounded
retries, credential replacement or manual finalization of failed receipts. Keep
Claude and Zcode in scope. Preserve gateway restoration and exact PR ledgers.
