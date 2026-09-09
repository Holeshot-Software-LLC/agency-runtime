---
title: "Preserve completed-task subject context and repair Claude installation"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, native, context]
related:
  - docs/roadmap/issue-AR-421-preserve-completed-task-followup-context.md
  - docs/roadmap/issue-AR-422-preserve-claude-update-permissions.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: worklog
commit: cf4ed77fb52a8355441fba7949d309a576ff86ee
short: cf4ed77f
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/810
related_issues:
  - docs/roadmap/issue-AR-421-preserve-completed-task-followup-context.md
  - docs/roadmap/issue-AR-422-preserve-claude-update-permissions.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Preserve completed-task subject context and repair Claude installation

## Purpose

The fixed native sample reproduces an ordinary short follow-up staffing failure.
The preceding review completes, but "go for it" loses its bounded subject before
staffing. Separately, repeated Claude npm updates undo temporary permission fixes.

## Approach

Classifier6 preserves correlation for completed-task contextual replies and
revisions, always requiring fresh selection and execution decisions. Completed
workers are never replayed. Existing transcript-free context, source-state guard,
independent critic and validators remain unchanged; old classifier versions stay
readable. New explicit tasks, failed terminal states and untrusted context do not
inherit completed-task correlation.

Claude's own updater receipt matches its latest namespace replacement. An inert
offline npm fixture reproduces775parents under process002/additional npm mask0.
Mask022 does not repair every path, so no npm user config was changed. The native
installer under077 provides its supported versioned binary and PATH launcher.
Normal trust and Agency refresh pass; active user terminals remain untouched.

## Challenges encountered

One initial regression command accidentally imported candidate source through
pytest's root configuration. It is not original-source evidence. The corrected
negative control imports and asserts original classifier5 before pytest starts;
seven positive regression cases fail and12negative cases pass. Ruff's complexity
limit required extracting the terminal contextual-reply decision without changing
active-turn behavior. Original-source integration fails with missing context.

## Decisions and alternatives

ADR-0064/0163 govern bounded correlation and fresh inference. ADR-0055 governs
executable identity: use the host's native installer, never copy or weaken trust.
A complete response without accepted staffing remains a failed suite result.

## Verification

Focused152pass; original-source negative control7fail/12pass. Named production
spine1151pass/3skip in117.94s; UI224pass; Ruff check/format pass. Native Codex
baseline review73.147s/multi-step114.055s have exact accepted terminal hashes;
short follow-up84.122s fails staffing. Native injection inspection and remaining
hosts are pending. No exhaustive or Windows dispatch.

## Follow-ups

Install a verified candidate artifact, repeat the same fixed requests and obtain
isolated acceptance forAR-421/422. Complete Hermes default adoption, OpenClaw
injection and Zcode answering gates underAR-404. Preserve every baseline outcome.

## Baseline continuation

Codex full cards match every exact selected Store version on the review and
multi-step turns, and their accepted terminal hashes match stdout. The failed
short follow-up is retained. Hermes normal native review187.194s has exact card
in native API context and matching accepted response; short follow-up times out
at360s (363.486s including termination), with recruiter and critic each timing
out after120s. Multi-step times out at360s (368.628s including termination), Store
interrupted. Both failed cases remain in evidence.

OpenClaw's bounded four-session observer was installed using native capability
consent and approved normal gateway maintenance. Stop initially refused without
the explicit operator-service flag; confirmed stop/install/start all exit0 and
RPC is healthy. Only plugins configuration changed. No delivery was requested.

Candidate artifactdb1c642f built and independently verified; wheel SHA256
9592253ba3d90d362d1ed05daaf641243f2cf598b6d87d5a0a9df28e96c7face.
Initial conformance baseline failed because inherited umask002 creates unsafe
test paths. Corrected invocation sets process077, preserves the failed report,
and is still running. Additional selector/context43tests pass. One earlier
command named a nonexistent test file and ran no tests; corrected selection
is the43pass result. Candidate installation waits for the frozen baseline.

## Installed repair checkpoint

Frozen conformance now passes188/188 with no surviving/invalid mutation and
unchanged production source. Verified wheeldb1c642f is installed; a fresh isolated
interpreter reports classifier6 and all614package files match the wheel exactly.
Normal gateway stop/install/start succeeds. Staffing model settings remain unchanged.

OpenClaw baseline review143.701s answers without accepted staffing after a planner
timeout; follow-up353.101s fails natively and multi-step hits the360s process
deadline (361.216s including termination). All are retained. The initial observer
manifest lacked startup activation: installed metadata did not prove callbacks
were imported. Startup activation is now declared and normally reinstalled;
its after-repair native input evidence is still pending.

Read-only LiteLLM model info proves host routing differs: Hermes/OpenClaw override
all Agency routes with task-agency-router/Mistral Small3.2 24B, while Codex uses
separate planner/recruiter/critic pools. Pool membership does not identify a
historical selected backend. A minimal removal of the two host overrides is
prepared and validated, but awaits the owner's model/cost choice.

Claude same-version native reinstall under process002 preserves the exact binary
and normal executable trust. Zcode's existing enabled desktop Z.AI provider now
fills the missing CLI model config; hooks are unchanged and no new credentials
were provisioned. Fresh Claude/Zcode native turn gates remain.

## Native projection and activation gates

The first post-wheel Codex sample still ran frozen projection6e7dc299c23e and
classifier5: review100.569s, follow-up72.701s, multi-step106.534s. All finalized,
but the follow-up selected product/change-management specialists. These attempts
do not exercise the repair and are retained with that explicit limitation.
Normal native refresh now publishes projection1825059191a2/classifier6 for all
five hosts. Codex plugin64c34689b8a1 is enabled, but native hooks/list reports
all8events modified/0trusted. Its next8.231s/8.731s/11.086s answers have no Agency
receipt and are retained as activation failures. No trust hash was edited.
Owner native approval is pending; no further Codex provider retry occurs before it.

Claude's first fresh native review57.602s uses classifier6, accepts code-reviewer,
contains its exact selected full card in correlated hook_additional_context, has
all five Store-matching headers and an accepted exact response hash. Remaining
fixed cases run sequentially. Hermes/OpenClaw staffing-model alignment remains
unapplied while awaiting the owner's choice.

Current Hermes upstreambf53ff00a7 was inspected in a new owned worktree. The two
existing invariant tests reproduce5failures (two truncated-loop variants and three
printable-failure exit variants). An initial runner used the release interpreter
without pytest and started no tests; corrected native runner uses the dev venv.
The historical patch is being ported to extracted turn phases; no default Hermes
source or upstream branch has changed.

## Claude fixed sample completion

Review57.602s has complete native evidence. Follow-up190.045s has classifier6,
continuation_of the exact completed review, fresh selection/reroute, correct code
and accepted matching hash. Its15.7KB hook output was replaced by Claude's native
persisted-output pointer; full inline specialist cards are not proved. Multi-step
104.114s fails staffing. These outcomes remain in the fixed sample. The context
repair does not establish whole-system staffing reliability.

Hermes native port30f421ecce onbf53ff00a7 passes31focused tests and the
2091pointer compatibility scan. A partial first edit left a missing turn_id and
three unmodified CLI assertions; that failed run is retained before the final
31pass run. Native source is committed in its owned worktree; default unchanged.

Hermes port is published for upstream review asPR106490 (NousResearch/hermes-agent),
commit30f421ecce; no upstream merge permission is available. AR-423/#811 records
the Claude native hook-output finding. Zcode initially received the runtime object
instead of the file-schema model reference, so both native launches failed before
provider execution. The corrected file uses the same existing provider/credentials
and leaves hooks unchanged; exact before/after hashes and failures are retained.

Native PR106490 is now ready for upstream review; fork rights do not grant
permission to merge NousResearch/main. Documentation checks caught an external
repository URL and invalid status names in the new local record; corrected to
a self-contained patch reference and canonical open status.

## Zcode corrected-schema sample

Review81.564s and follow-up71.652s have all five Store-matching headers, exact
accepted output hashes and full selected cards in native model_io requests.
Native CLI trace IDs differ from Agency trace IDs: the extraction binds the exact
CLI session/native trace and requires the Agency trace in that request context.
Classifier6 continuation points to the exact review and preserves fresh routing.
Multi-step86.877s returns exit0 but fails staffing with critic_wrong_neighbor_selection;
that failure is retained, not called a successful sample.

AR-421/422 builder records are prepared for isolated verdicts, scoped respectively
to completed-task context and native executable permissions. Initial dry-run
caught an out-of-range test citation; corrected references pass. No verdict is
authored by the builder.

## Refreshed Hermes and Claude boundary checkpoint

Hermes unchanged native7cd91114 with Agency classifier6 completed the review in
299.269s, of which routing records268.702s. Native user api_content is bound by
the exact supplied request and following assistant accepted response hash in the
same session; the full selected card, all five headers and finalization match.
Follow-up365.059s and multi-step364.591s hit the360s deadline and are interrupted;
no acceptance was manufactured. See AR-404-hermes-suite-after-repair-20260909.json.

Claude installed2.1.266 native JavaScript uses a10,000UTF-16-code-unit default
for hook additionalContext persistence. The observed15.7KB is output size, not
the threshold. Four exact cards alone exceed the native inline ceiling. AR-423
retains the binary hash and bounded limiter excerpt; no native binary was edited.
OpenClaw's observer now takes the native event runId with context fallback; normal
stop/install/start completed and read-only RPC reports healthy. The unchanged-route
fixed sample is running. Codex attended hook trust and staffing-route choice remain
pending; no configuration alignment or repeated Codex provider turn was performed.

## OpenClaw refreshed sample and observer correction

September 9 refreshed sample: review 209.513s has accepted staffing, all five
Store-matching headers and exact central accepted response hash. The observer
captured no input because native registration explicitly rejected missing
plugins.entries.ar404-native-witness.hooks.allowConversationAccess. Follow-up
352.602s fails after separate recruiter/critic 120s timeouts; multi-step 361.217s
hits the outer deadline. All remain in AR-404-openclaw-suite-after-repair-20260909.json.
A documented per-plugin permission grant and one new ordinary review are prepared,
with five exact allowed session keys, bounded local output and no delivery.

Native plugin install capability acceptance did not grant conversation-hook access;
metadata-only inspection also did not prove runtime import. The exact native log
rejections and next one-attempt probe are retained in
AR-419-openclaw-observer-permission-20260909.json. No earlier missing card proof
is retroactively promoted. A transient remote internal-server-error rejected one
push; a single retry published the same branch unchanged. Final policy-availability
check needed explicit PYTHONPATH after a launcher import error; corrected check passes.
