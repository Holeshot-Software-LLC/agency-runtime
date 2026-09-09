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
branch: codex/ar404-shared-staffing-20260909
evidence_commit: b62c31c7ea6fecae5bd407e9bd2e2730d055d4f4
minimum_ledger_commit: 6a3dc1541da56d94426046b9a628a00c9187d130
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native reliability repair checkpoint

## Checkpoint

Package base main f013e63a follows PR814 and ledgerPR815. AR-421/422/424
closed with isolated evidence; AR-404/418/423 open; AR-419 now isolated-complete. New owned branch
codex/ar404-shared-staffing-20260909 applies the approved shared staffing config.
Only Hermes/OpenClaw overrides removed; other settings/answering models unchanged.
Fresh Codex inspection: all8hooks enabled/trusted, no modified/missing entries.
Claude per-tool grant is pending; /permissions instructions are now documented.
Installed production cd86e40a/artifact0cd4f289 unchanged,615files match. Claude/Zcode
projection07d88875a9e6; Codex/Hermes/OpenClaw1825059191a2. This parent has a stale
long-lived integration and previously failed finalizer transport. Fresh processes
must supply native evidence. Earlier branches are historical and merged.

Shared Hermes phase: review86.111s/routing56.290s passes all native gates;
follow-up83.279s critic rejection; multi-step87.094s response_invalid. No retry.
Evidence: AR-404-hermes-suite-after-shared-staffing-20260909.json.

OpenClaw shared phase: review57.109s and multi95.268s fail staffing; follow-up
53.401s passes exact native card, five headers and one matching accepted terminal.
AR-419 second isolated pass satisfies all4criteria. First absent verdict retained;
existing host-hooks94 and terminal/boundary48 pass. Scope: ordinary CLI boundary.

Fresh Codex shared phase: review62.855s/follow-up53.903s pass all native gates;
multi-step100.324s fails staffing. Classifier6; exact executing projection hash
not exposed in native context. Observer removed and gateway RPC healthy.

## Completed evidence

Frozen evidence/AR-404-reliability-suite-20260909.json fixes ordinary review,
same-session "go for it" and multi-step correction on five hosts, one attempt per
case/phase,360second process cap. Preserve every failed and blocked attempt.

Codex baseline review73.147s/multi114.055s have exact cards, headers and accepted
hashes; follow-up84.122s fails staffing. Post-wheel sample still used classifier5
and is invalid repair evidence. Post-refresh sample answered with no Agency
receipt because8modified hooks were untrusted. The current fresh inspection confirms
all8trusted; the fresh review and follow-up now pass, multi-step fails staffing.

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
RPC healthy. After-refresh review209.513s has exact accepted hash/headers; follow-up352.602s
fails staffing and multi361.217s times out. Missing per-plugin conversation-access
permission, explicitly logged by native registration, explains absent observer events.
Documented permission is now granted; runtime imports3hooks. Startup RPC initially
was not ready, subsequent read-only probe passes. One new ordinary probe226.500s captures all3callbacks but fails staffing
(recruiter timeout and malformed fallback). No selected cards/accepted finalization.
That observer was normally removed, native RPC healthy. The shared-staffing
phase reinstalled it for two new exact keys, captured input, then removed it;
native RPC is healthy.
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

AR-423/424 source cd86e40a / artifact0cd4f289 merged via PR814. AR-424
closed with isolated byte-preservation evidence. AR-423 emits a bounded frame
and exact selected-version MCP requests; its four-card native probe was denied
by normal tool permissions. Ordinary inline delivery passed; full MCP delivery
and AR-423 isolated acceptance remain pending. See its capsule and worklog.

The owner reports Codex trusted; fresh hooks/list confirms8trusted/0modified.
Fresh review and follow-up prove staffing, injection and accepted finalization;
the separate multi-step still fails critic selection.
The owner now authorizes shared staffing. Hermes/OpenClaw override removal is
applied; all five hosts resolve identical requested per-stage profiles. This is
not proof of identical actual backend selection, speed or reliable responses.
Claude's two native MCP Allow rules remain pending a normal owner grant.

Hermes upstream port30f421ecce onbf53ff00a7 is ready nativePR106490. Repository
stores the complete AR-418-hermes-upstream-terminal-20260909.patch. Five red
variants reproduced; final31focused tests and2091compatibility pointers pass.
No upstream merge permission; default checkout unchanged. Original provider
truncation cause/token cap unproven. OpenClaw exact input and accepted terminal
are proven on its follow-up; all4isolated criteria are satisfied.

## Same-task continuity

PR816 owns this package. After merge, this branch is historical; create a new
owned worktree for new changes. Continue the same task. At/below50percent,
checkpoint the smallest substantive/ledger pair and continue. No transfer or
empty continuation for telemetry. Preserve unrelated and Windows work.

## Next bounded work package

Investigate the exact retained recruiter/critic and missing-header failures under
AR-404 before another bounded phase; no unchanged-condition retry.
The shared-staffing phase is complete with every failed case retained.
No observer remains; normal gateway RPC is healthy.
Wait for Claude's exact per-tool grant before repeating its card surface probe.
Zcode review/follow-up passed but multi-step failed; retain that scope and evidence.
No manual specialists, altered critic decisions or unchanged-condition retries.

## Verification

Current production cd86e40a: expanded focused166pass/6skip, spine1151pass/3skip,
UI224, Ruff784files, routing, docs1357 and tracker415 pass. Original native-hook
negative control emits15076UTF-16 units; original shared-host card-byte test fails.
The repaired shared-host case passes separately. Fresh-source conformance188/188,
no survivors or invalid mutations, source unchanged. Packaged smoke and canonical
build/distribution verification pass; installed615files exactly match the wheel.
AR-424 initial criteria1/2 satisfied; criterion3 absent on provenance, retained.
Second packet includes exact production/test tree identities and the named check;
all three second-pass verdicts are satisfied (04121983, 6dbff237, 5b3a847c).
No exhaustive corpus, coverage gate, compatibility or Windows matrix dispatched.

## Constraints

Inference alone selects staff. Preserve critic, validators, trust and scope. No
manual specialists, unbounded retries, manual failed-receipt finalization or
external messages. Keep Claude and Zcode explicitly in scope. Owned worktree → PR
→ merge with exact worklog rows. Close only scopes with isolated acceptance.
