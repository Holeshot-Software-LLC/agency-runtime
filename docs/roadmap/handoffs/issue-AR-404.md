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
branch: codex/ar404-reliability-suite-20260909
evidence_commit: c13f3b72730d1790280e4696b7974742dd2eb722
minimum_ledger_commit: f78878b2aba68d49e3716c3929eb34a3010baa6e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native terminal repairs and remaining gates

## Checkpoint

PR799 merged at58247849. Repair/evidence branch is historical. This recovery
branch records the merged checkpoint; if merged, create a new owned worktree.
PR803 merged as263a0ec3 with the AR-420 repair and isolated acceptance.
Its branch is historical; create a new owned worktree for new changes.
Installed immutable source3fe3d7ba contains OpenClaw repair94b9eb28 and
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

AR-421/#808 candidate fixes completed-task context loss with fresh inference.
Focused152pass; original version5 negative control7fail/12pass, including actual
preflight handoff. Production1151pass/3skip, UI224, Ruff pass. Not installed yet.
Codex frozen baseline: review73.147s and multi-step114.055s completed with exact
accepted hashes; same-session "go for it"84.122s staffing failed. Native card
inspection pending. See evidence/AR-404-codex-suite-baseline-20260909.json.

AR-422/#809: latest Claude npm update receipt2.1.261to2.1.266 matches directory
replacement. Process umask002/npmadditionalmask0 explains775parents. Offline
fixture proves npm configmask022 alone leaves writable root/executable; no npm
config changed. Supported native install2.1.266 under077 now owns native PATH
launcher,700parents; normal executable gate and Agencyrefresh pass. Existing
user terminals untouched. Native turn/update-survival gates pending.

Hermes native candidate59e52e556a remains unpublished/default unadopted;
34native/94adapter tests and one source-candidate success are historical. Baseline
suite now uses normal `hermes chat --oneshot --quiet`, no approval bypass.
Original truncation cause/token cap remains unproven. OpenClaw terminal fix
is historical live-proven; exact input card remains pending bounded observer.
Zcode native executable exists but its CLI answering model config is missing.

## Same-task continuity

Read the linked native-refresh worklog and2026-09-08-native-terminal-repair.md.
The branch field is provenance; recheck merge state and use a new owned branch
for subsequent changes.
At or below50percent remaining, checkpoint the smallest safe evidence/ledger
pair and continue. Preserve unrelated worktrees and operator files.

## Next bounded work package

September9 owner approved the reliability package. Baseline77f6773f clean and
synchronized; new owned branchcodex/ar404-reliability-suite-20260909.
Freeze and run evidence/AR-404-reliability-suite-20260909.json: review, same-session
"go for it", multi-step correction on Codex/Hermes/OpenClaw/Claude/Zcode, one
attempt per case per phase,360second deadline. Retain failures and blocked gates.
Record exact proposal/critic/stage timings where native observation supports it.
Fix reproduced causes with regression tests and repeat the same suite; no claim
of general reliability from a15turn sample. Host gates remain required.

Current trace01a08595-581c-7853-89e1-f1a8e2e9b50c failed. Read-only reconstruction
matches persisted state revision: completed prior task context existed, but
"go for it" classified new intent and preflight discarded that context. Failed
proposal unavailable; critic veto unadjudicated. Reranker passed, cold embedding
39.653s. See evidence/AR-404-followup-failure-20260909.json. Investigate context
loss without weakening inference, critic or validator boundaries.
AR-420 is scoped acceptance-closed; remaining reliability stays withAR-404.
Claude native executable trust now passes; verify native turn and update survival.
Keep user terminals intact. Complete Hermes default adoption, OpenClaw exact injection,
and Zcode answering setup using existing authorization and supported native gates.

## Verification

AR-420 focused164, conformance188/188 and docs1345pass on unchanged production
source5ff8e85c. Claude2.1.265 parents reverted to775; restored755, normal gate
and three isolated verifier runs pass. Mutation cause unproven.
Prior host focused94passed; native Hermes34passed; production1151passed/3skipped; UI224;
Ruff/docs/metadata/routing pass. Earlier8921c77e frozen conformance188/188 passes,
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
