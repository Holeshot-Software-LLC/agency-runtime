---
title: "AR-419: Finalize ordinary OpenClaw CLI responses with exact evidence"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-09
tags: [openclaw, cli, lifecycle, finalization]
related:
  - docs/worklog/2026-09-08-native-terminal-repair.md
  - docs/decisions/0016-central-finalization-and-session-correlation.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-08-hermes-openclaw-native-refresh.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-419
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/797
depends_on: []
blocks: []
---

# AR-419: Finalize ordinary OpenClaw CLI responses with exact evidence

## Problem

An ordinary native CLI response can contain the correct Store-backed header and
accepted staffing, yet leave Agency active with zero finalization events. Native
ok/completed status does not establish a centrally accepted response.

## Current state

### Shared staffing native OpenClaw phase

Fresh ordinary CLI follow-up7bdd5df5-248a-48a1-aa2b-3667c35a2200 returns the
correct function in53.401s. Native llm_input with exact session/run contains the
complete selected card; five fields match Store; one authoritative accepted terminal
event binds response6d17389d102fb011d7aadc6d48f37a75a865f4f632d0b16513d55e314e3abbdf.
No --deliver, external message or manual finalization. The initial57.109s review
and95.268s multi-step fail staffing and stay in the same fixed-phase evidence.
Exact focused91passed/1skipped; the first command named a nonexistent test file
and ran no tests, retained in the packet. Isolated AR-419 verification follows;
this candidate does not establish all-host or all-case reliability.


The declared observer probe returned in226.500s, native trace
a24020c3-c3d0-43e2-bf10-230965702e21. Native llm_input, before_agent_finalize and
agent_end callbacks are captured under the exact session/run. Staffing failed: primary
recruiter timeout, then malformed/non-JSON bounded fallback responses. No specialists
were selected and no accepted finalization exists. This is callback proof only;
AR-419 stays open. No unchanged-condition retry was performed. Normal observer
uninstall removes its permission and files; gateway RPC is healthy and every
non-plugin/non-meta configuration section remains unchanged.

September 9 refreshed sample: review 209.513s has accepted staffing, all five
Store-matching headers and exact central accepted response hash. The observer
captured no input because native registration explicitly rejected missing
plugins.entries.ar404-native-witness.hooks.allowConversationAccess. Follow-up
352.602s fails after separate recruiter/critic 120s timeouts; multi-step 361.217s
hits the outer deadline. All remain in AR-404-openclaw-suite-after-repair-20260909.json.
A documented per-plugin permission grant and one new ordinary review are prepared,
with five exact allowed session keys, bounded local output and no delivery.

September 8 continuation: the installed OpenClaw terminal callback is awaited
before CLI delivery. Its native context identifies internal delivery as
`channel=webchat`; the generated handler previously returned `allow_pending`
without invoking the existing exact-text outbound gate. The candidate now invokes
that gate only for this explicit native channel after a valid pre-verify result.
Other channels retain their full-payload sealing path. Twelve executed Node
callback cases cover the channel and policy split; focused integration passes
153 tests with one existing skip. Fresh installed terminal proof passes: trace
`b2f9ef9e-1280-4c28-9934-6b094bdfcf6a` has one authoritative accept event, exact
visible-response hash81356a9c914b08463d76681650c7daf4ae24ad6d4236a880dff15df54066c466
and completed Store state. All614installed files match verified308b670a wheel.
Exact card injection remains unproven; a temporary observer requires separate
native capability consent. See evidence/AR-419-openclaw-terminal-20260908.json.
Named spine1151/three skips, UI224, docs/Ruff/routing and conformance188/188 pass.

Fresh refreshed-gateway tracebfbdfdc5-59b8-481d-b0d6-8e4f4abc872a;
Agency sessionagent:openclaw:ar404-native-20260908-2006;
native sessionccce9bc3-4818-4454-b5bd-6ade5ded98fb. Total116.524s, staffing91.052s.
Inference selected code-reviewer, read-only scope. All five response fields match
current Store via installed fill_header_fields. Native returned a correct review,
statusok/completed, stopReasonstop and no tool calls. Agency remains active/ready,
terminal_finalization_id=null and zero finalization events.

The installed node bridge accepts a valid pre-verify policy result as
allow_pending without committing success. The generated ordinary agent_end
handler maintains native error markers rather than finalizing responses. Those
source paths identify a boundary to inspect; exact callback invocation must still
be demonstrated. Existing explicit native finalizer-tool successes do not prove
that ordinary headed responses take a complete automatic lifecycle.

Exact specialist-card delivery remains unproved: native prompt.submitted text
is redacted; finalPromptText is only the caller's350characters. Prompt accounting
and a matching output identity cannot substitute for exact injection evidence.
The bounded artifact is evidence/AR-404-openclaw-native-20260908.json.

## Approach

Trace the actual CLI terminal callback and valid allow_pending path. Establish
an exact session/run/response-bound terminal handoff through central finalization
without manual acceptance of the old run. Preserve first-invalid terminal
semantics, outbound seals, native-error delivery, inference-owned selection and
critic independence. Capture exact model-facing specialist context through a
supported native evidence surface. Do not invent success from CLI exit0.

## Dependencies

ADR-0016 central finalization and correlation, plus the native OpenClaw lifecycle.
AR-404 preserves current installed-copy and gateway-maintenance evidence.

## Acceptance

- [ ] The ordinary headed CLI response reproduces the missing terminal event,
      and its actual native callback/central-finalization boundary is identified.
- [ ] A fresh ordinary installed native turn has exact card injection evidence,
      truthful headers and a centrally accepted matching response hash.
- [ ] Malformed and cross-run evidence, first-invalid terminal behavior, native
      errors and outbound seals retain their existing rejection boundaries.
- [ ] Focused and production checks pass, with exact repository, tracker and
      worklog records and no manual acceptance or weakened staffing contract.
