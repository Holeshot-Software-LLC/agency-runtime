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
branch: codex/ar418-ar419-native-terminal-20260908
evidence_commit: 94b9eb28e99c7a9085e6ff6ab4638e506d25e313
minimum_ledger_commit: 308b670ad2d8d600b96ab690100e3c0ce231c254
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 Hermes and OpenClaw native verification

## Checkpoint

Owned branch starts from clean synchronized main97e269ec. PR799 is open.
Installed immutable source308b670a contains OpenClaw repair94b9eb28; all614
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
refresh succeeds. Native turn remains to be run with explicit build permissions
because native headless default is yolo. This is executable proof only.

## Exact blocker

Hermes output-limit early returns bypass native finalizer/session-end callbacks;
outer runner and CLI can misclassify printable partial output as success. No
supported terminal-result hook covers those returns. AR-418 needs native-boundary
repair, not fabricated adapter success. Original provider cause/token cap unproven.
OpenClaw exact injection observer requires native capability consent, asked once;
no observer was installed. Do not treat elapsed time as approval.

## Same-task continuity

Read the linked native-refresh worklog and2026-09-08-native-terminal-repair.md.
Continue in the named owned branch; old capsule branches are merged history.
At or below50percent remaining, checkpoint the smallest safe evidence/ledger
pair and continue. Preserve unrelated worktrees and operator files.

## Next bounded work package

Run one ordinary Zcode trial against the repaired native entrypoint, preserving
inference/critic/validators. Repair the native Hermes failure boundary and prove
ordinary success. If owner consents, use the session-scoped OpenClaw observer
for exact input evidence, then remove it and restore gateway RPC health. Close
issues only after isolated acceptance. Merge PR799 with exact merge ledger.

## Verification

Candidate focused153passed/1skipped; production1151passed/3skipped; UI224;
Ruff/docs/metadata/routing pass. Candidate frozen conformance188/188 passes,
source unchanged, after private umask077 correction. No exhaustive dispatch,
Windows matrix or all-host certification. Prior Codex56.656s roundtrip is historical
comparison evidence; current Codex preflight failed and is honestly unstaffed.
Exact prior handoff receipt preserves critic_wrong_neighbor_selection; no transport
recurrence or erroneous veto is inferred. Fresh Codex hook projection still unproven.

## Constraints

No manual specialist selection, trust bypass, weaker validator/critic, unbounded
retries, credential replacement or manual finalization of failed receipts. Keep
Claude and Zcode in scope. Preserve gateway restoration and exact PR ledgers.
