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
evidence_commit: 8aa7214898a8c9cc0ae5448cd54d6663c3fa7e8a
minimum_ledger_commit: efeab69637e5bb47d15152fa827ba83735b8f855
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native reliability repair checkpoint

## Checkpoint

Main was clean/synchronized77f6773f. Owned branch
codex/ar404-reliability-suite-20260909; draftPR810. Production repaircf4ed77f,
artifact source db1c642f. Verified installed wheelSHA256
9592253ba3d90d362d1ed05daaf641243f2cf598b6d87d5a0a9df28e96c7face:
all614package files match; fresh isolated interpreter reports classifier6.
No all-host completion. AR-404/418/419/421/422 remain open; AR-414/415/420 closed
only against their isolated scopes. Preserve Windows and unrelated work.

## Completed evidence

Frozen evidence/AR-404-reliability-suite-20260909.json fixes review, same-session
"go for it", and multi-step correction on five hosts, one attempt/case/phase,
360second process cap. Keep every failure and blocked gate.

Codex baseline: review73.147s and multi-step114.055s have exact selected cards,
truthful Store headers, accepted exact hashes and completed status. Follow-up
84.122s fails staffing. See evidence/AR-404-codex-suite-baseline-20260909.json.

Hermes baseline: normal review187.194s has full exact card in native API context,
matching accepted hash and completed Store. Follow-up times out360s (363.486s
with termination), recruiter and critic each120s timeout. Multi-step also hits
360s (368.628s), Store interrupted. Both failures retained in Hermes suite evidence.

OpenClaw baseline: review143.701s failed staffing after planner timeout; follow-up
353.101s failed natively; multi-step process timeout361.216s. No accepted claim.
Initial observer was installed but lacked startup activation; no input events were captured.
Corrected manifest now declares startup/hook activation and was normally installed
with native capability consent. Only plugin settings changed. No delivery.

Claude native2.1.266 installation fixes PATH trust. Npm updater receipt explains
775parent recurrence under process002/npm additional0. Offline fixture proves
npm configmask022 alone is insufficient. Supported native install under077 yields
700parents; normal Agency refresh succeeds. Reinstall under002 preserves exact
binary and trust. User terminals remain intact; fresh native turn pending.

Zcode CLI0.16.5 remains installed from desktop3.10.2 bundle. Missing answering
config now uses the existing enabled desktop Z.AI provider/GLM-5.3; hooks unchanged,
no new credentials. Native answering and finalization remain pending.

## Exact blocker

AR-421/#808 fixes completed-task context loss with fresh staffing. It preserves
source guard, transcript boundary, independent critic and validators. Needs fresh
installed native follow-up and isolated acceptance; installation is not the gate.

Hermes/OpenClaw staffing models differ from Codex: their host default overrides
select task-agency-router/Mistral Small3.2 24B instead of the shared separate pools.
Read-only model-info evidence is in AR-404-staffing-route-comparison-20260909.json.
Removing only those two overrides is prepared and validated. Owner choice pending:
it changes backend models/cost, so do not apply without the answer. Native
answering models are unaffected by that proposed change. Pool membership is not
proof of a historical selected backend or a controlled latency benchmark.

Hermes truncation patch59e52e556a remains a tested source candidate, unpublished
and unadopted by the normal native checkout7cd91114. Upstream bf53ff00 has refactored
truncation into agent/turn_truncation.py and still returns incomplete results;
do not blindly transplant the old patch. Original provider cause/token cap unproven.
OpenClaw exact input proof still requires observing callbacks on an accepted turn.
AR-422/#809 needs native answering and isolated acceptance after the trust repair.

## Same-task continuity

Read2026-09-09-completed-task-context.md and the frozen suite/evidence. Existing
PR799/803/806 records remain historical. Continue from the owned branch, not an
old merged branch. At/below50percent, checkpoint the smallest safe evidence/ledger
pair, then continue the same task; never stop or create a new task for telemetry.

## Next bounded work package

Run the fixed after-repair sample on fresh native processes. Start with Codex;
keep Hermes/OpenClaw model-route choice pending while progressing Claude/Zcode
if necessary. Corrected OpenClaw observer is limited to exactly four suite session
keys,16events/session,1MiB/event,8MiB/process. Remove it normally after evidence.
Preserve all outcomes and state/model configuration fingerprints. No outer retry
under unchanged conditions. Isolated acceptance precedes issue closure.
Complete native Hermes adoption through a reviewed normal path; original patch
and historical candidate-source success do not establish current default repair.

## Verification

Focused152pass, plus selector/context43pass. Original classifier5 negative control
7fail/12pass. Production spine1151pass/3skip; UI224; Ruff782files, docs1349,
tracker413, routing pass. Frozen conformance188/188 passes under process077;
initial002baseline failure is retained, no mutation ran in that failed attempt.
No exhaustive corpus, coverage gate or Windows matrix dispatched.
Prior fresh Codex published-projection hash remains unproved: status lacks hash;
no bwrap/trust bypass. New native classifier6 evidence must come from a fresh turn.

## Constraints

Inference alone selects staff. No manual specialists, weaker critic/validators,
unbounded retries, manual failed-receipt finalization or external message delivery.
Keep Claude and Zcode explicitly in scope. Restore gateway health and maintain
owned-worktree/PR/merge/exact worklog records. Close only scoped evidenced gates.

## Latest native projection gate

Post-wheel Codex still used classifier5; native refresh now publishes1825059191a2
(classifier6), plugin64c34689b8a1. Native hooks/list:8modified/0trusted; next three
answers had no Agency receipt. Both samples retained; owner terminal hook trust
is pending, no hash edits or further unchanged retries. Claude review57.602s has
classifier6, exact card, all headers and accepted hash; remaining cases pending.
Hermes upstream port in owned worktree onbf53ff00a7 has5red invariant variants;
default Hermes unchanged. Model alignment remains unapplied pending owner choice.

Claude suite ended: review57.602s complete evidence; follow-up190.045s classified
continuation with exact previous trace/fresh staffing, but native15.7KB hook
output became a persisted-output pointer (full inline cards unproved); multi-step
104.114s failed staffing. Zcode fixed native sample is next.

Hermes port30f421ecce:31tests pass, nativePR106490 ready for review; default unchanged.
AR-423/#811 tracks Claude hook pointer substitution. Zcode schema corrected from
runtime object to provider/model reference; first invalid launches retained.
