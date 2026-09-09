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
evidence_commit: 73a127ac100641050a558cac08b1fb76b2cca2ff
minimum_ledger_commit: 5bd8e013720da7abefcb0c30fb73aa1503ad43e7
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native reliability repair checkpoint

## Checkpoint

Main was clean/synchronized77f6773f. Owned worktree branch
codex/ar404-reliability-suite-20260909; draftPR810. Production repaircf4ed77f,
artifact source db1c642f. Wheel SHA256
9592253ba3d90d362d1ed05daaf641243f2cf598b6d87d5a0a9df28e96c7face:
all614package files match; fresh isolated interpreter classifier6. Native refresh
publishes1825059191a2; Codex plugin64c34689b8a1. No all-host completion.
AR-404/418/419/421/422/423 open; AR-414/415/420 closed only against isolated scopes.

## Completed evidence

Frozen evidence/AR-404-reliability-suite-20260909.json fixes ordinary review,
same-session "go for it" and multi-step correction on five hosts, one attempt per
case/phase,360second process cap. Preserve every failed and blocked attempt.

Codex baseline review73.147s/multi114.055s have exact cards, headers and accepted
hashes; follow-up84.122s fails staffing. Post-wheel sample still used classifier5
and is invalid repair evidence. Post-refresh sample answered with no Agency
receipt because8modified hooks are untrusted. No additional retry pending trust.

Hermes baseline review187.194s has complete evidence; follow-up363.486s and
multi368.628s time out. After-refresh review299.269s has complete evidence and
classifier6; routing268.702s. Follow-up365.059s and multi364.591s hit the360s
limit, Store interrupted. Exact current review native session20260909_071950_034119,
trace20260909_071950_034119:2e31f4e2-957d-47b3-9056-2b159c647824:2b8ee4fc.
Full card is in native api_content for the exact request preceding the accepted
assistant hash in that session. Default native Hermes remains7cd91114.

OpenClaw baseline review143.701s fails staffing after planner timeout; follow-up
353.101s fails natively; multi361.216s process timeout. Corrected bounded observer
has startup/hook activation and event.runId correlation. Normal maintenance exits0,
RPC healthy. After-refresh sample on unchanged staffing routes is running.
No external delivery. Metadata alone is not callback/card proof.

Claude native2.1.266 PATH repair uses its supported native installer, not npm.
Inert fixture reproduces775parents under process002/npm mask0; npm022 alone is
insufficient. Native parents700, executable755; same-version native reinstall
under002 preserves binary and trust. Fresh review57.602s has exact card, headers,
classifier6 and accepted hash. Follow-up190.045s correlates exact review with
fresh staffing and accepted hash but native hook output becomes a15.7KB persisted
pointer. Native default limit10,000UTF-16 units; four cards alone exceed it.
AR-423 owns delivery repair. Multi104.114s fails staffing.

Zcode bundled CLI0.16.5 from desktop3.10.2 restored. Initial missing answering
configuration and our first incorrect runtime-object schema launches are retained.
Corrected file reference builtin:zai-coding-plan/GLM-5.3 reuses the existing desktop
provider/credential; hooks unchanged. Corrected review81.564s/follow-up71.652s
have exact cards, headers, accepted hashes and classifier6 continuation. Multi
86.877s fails staffing with critic_wrong_neighbor_selection. Native model_io proof
binds CLI session/native trace and Agency trace; their trace IDs differ.

## Exact blocker

AR-421 fixes completed-task context loss with fresh staffing; scoped isolated
builder prepared, now also cites Zcode full native follow-up. AR-422 native
executable builder prepared. No builder-authored verdicts; verify before closure.

Codex native trust requires the owner's fresh terminal startup review or /hooks;
8modified/0trusted. This long-lived conversation itself still reports the old
projection. Reinstall alone cannot refresh it. No trust hashes edited.

Hermes/OpenClaw host overrides select task-agency-router/Mistral Small3.2 24B,
not Codex's separate shared staffing pools. Read-only deployment comparison and
minimal candidate removing only two overrides are prepared. Owner choice pending:
changes models/cost; leave unapplied. Native answering models would be unaffected.
Historical backend selection and controlled speed equality are not established.

Hermes upstream port30f421ecce onbf53ff00a7 is ready nativePR106490. Repository
stores the complete AR-418-hermes-upstream-terminal-20260909.patch. Five red
variants reproduced; final31focused tests and2091compatibility pointers pass.
No upstream merge permission; default checkout unchanged. Original provider
truncation cause/token cap unproven. OpenClaw exact input remains to be observed.

## Same-task continuity

Read2026-09-09-completed-task-context.md and frozen evidence. Continue this owned
branch; capsule's older branches are historical/merged. At/below50percent,
checkpoint smallest safe substantive/ledger pair and continue the same task.
Never pause, create a new task or transfer for telemetry. Preserve Windows work.

## Next bounded work package

Finish OpenClaw fixed after-refresh sample; retain callbacks/cards/headers/hash or
exact failed gates. Remove the temporary observer normally and restore gateway
health. Run isolated AR-421/422 verdicts, deliver PR810 with exact merge ledger.
Continue remaining host repair: AR-423 delivery and Hermes normal upstream adoption;
Codex trust and staffing-model choice remain pending owner actions. No all-host
claim from ordinary successes while multi-step samples fail.

## Verification

Focused152pass plus selector/context43pass. Original classifier5 negative control
7fail/12pass. Production spine1151pass/3skip; UI224; Ruff782files; docs1352,
tracker414; routing pass. Frozen conformance188/188 under process077; initial002
baseline failure retained, no mutation ran then. Source unchanged sincecf4ed77f.
Worklog generated index2260commits current after moving our five rows inside its
marker. No exhaustive corpus, coverage gate or Windows matrix dispatched.

## Constraints

Inference alone selects staff. Preserve critic, validators, trust and scope. No
manual specialists, unbounded retries, manual failed-receipt finalization or
external messages. Keep Claude and Zcode explicitly in scope. Owned worktree → PR
→ merge with exact worklog rows. Close only scopes with isolated acceptance.
