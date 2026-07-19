---
title: "Use turn-scoped specialist activation with immutable session history"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-18
tags: [routing, evidence, tracing, finalization, fallback]
related:
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/roadmap/issue-AR-49-key-policy-cache-by-path-identity.md
  - docs/roadmap/issue-AR-46-bind-routing-to-store-config-identity.md
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/roadmap/issue-AR-26-bundle-default-coordinators.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-33-openclaw-final-outbound-seal.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0033-explicit-companion-route-availability.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0067-require-configured-inference-for-selection.md
  - docs/decisions/0068-select-compatible-specialist-closures-per-unit.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/decisions/0071-bound-native-delegation-correction.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0007-six-line-evidence-header.md
  - docs/decisions/0016-central-finalization-and-session-correlation.md
  - docs/decisions/0023-default-companions-for-trivial-messages.md
superseded_by: null
id: ADR-0045
type: decision
deciders: []
---

# ADR-0045: Use turn-scoped specialist activation with immutable session history

ADR-0064 refines the intent-classification boundary. References below to
`trivial` and `nontrivial` describe the retained compatibility projection, not
the authoritative decision about turn intent or roster participation.

## Context

Agency Runtime historically associated loaded specialists with a conversation
session. That was useful for audit, but finalization and Stop validation also
treated every historical load as active evidence. Long-running sessions therefore
accumulated stale header requirements and could retain competing specialist
instructions. Missing correlation at the public finalization boundary made the
opposite error possible: an empty lookup could be formatted as authoritative
`none` evidence.

The deterministic fallback policy already named `agents-orchestrator` and
`chief-of-staff`, but starter installations did not contain either agent. A
fallback that cannot be selected and retrieved when needed is not a runtime
contract.

## Decision

Continue to require the exact six-line Agency response header, but derive each
evidence field from the current correlated trace rather than cumulative session
state. Explanatory fields remain model-authored; runtime claims never are.

Keep specialist load events as immutable session history, but scope activation
and externally visible claims to the trace representing the current turn. Every
activation mutation carries both session and trace identity. Finalization, Stop
verification, delegation enforcement, and response headers query the current
trace; legacy session-only events remain historical and never become current by
inference. A new turn begins with no active specialists, so end-of-turn expiry is
structural rather than a mutable unload operation.

For persistent-parent hosts, treat a selected specialist as a plan. Only an
isolated work unit that the native host actually starts must consume a
single-use activation capability. Bind that capability to the exact
ready-recipe `slug`, immutable version, prompt hash, session, trace, and
work-unit identity; persist only the capability's digest. Fetch the authorized
prompt from immutable `agent_versions`, even if the active roster changes after
preflight. Completion compares every executed isolated unit with the full
consumed receipt set atomically and rejects missing, duplicated, stale, or
mismatched retrieval. It also requires a reciprocal native delegation event
with a host worker or tool-run identity for the same receipt and work unit.
Selected units that the host does not execute close through an explicit decline,
skip, or bounded `retry_exhausted` outcome; they never require or fabricate a
load receipt. A parent preflight, a native worker label by itself, or a
slug-only load can never manufacture exact-capability retrieval evidence.

Keep delegation recommendation and execution identity separate. The planned
`recommended_agent` is immutable once recorded. Native callbacks record the
truthful worker kind, worker identifier, and native run identifier separately.
A linked exact-version activation receipt records which specialist capability
was retrieved, but it never projects that specialist as the executing delegate.
Under the current unauthenticated MCP transport, delegated headers remain
`generic-worker`; capability retrieval and native execution stay separately
correlated and auditable.

The activation token is a work-unit capability, not cryptographic proof of which
process invoked MCP. Host-native tool arguments carry the same stable work-unit
label (`task_name` on Codex and `description` on Claude), and post-tool evidence
provides the independent execution binding. The transport does not authenticate
the MCP caller as the child: a parent could consume the capability itself and
then launch a same-labeled worker. The receipt therefore proves exact prompt
retrieval for the correlated work unit plus a native execution, not prompt
delivery to, or process-level consumption by, that child. A malicious parent
with authority to fabricate host evidence
also remains outside the in-process protocol's attestation boundary.

Bound specialist instructions before injecting them into the main agent. Use a
small count ceiling and a total character budget; preserve full historical names
for audit and dashboard reporting without reinjecting their prompts.

Use the compact resident `agents-orchestrator` and `chief-of-staff` binding for a
genuine no-match or justified abstention. Do not present that management
fallback as a semantic specialist match or append complete manager prompts to a
confident substantive route. Both managers are protected, bundled dependencies
on fresh installations. A proven pure acknowledgement may bypass ordinary
specialist selection, while conversation and other selection-requiring turn
kinds still consider the roster and may abstain explicitly. Direct-delivery
hosts load only the selected specialist prompt bodies into their bounded
current-turn capsule. On isolated hosts, selection remains a plan, and only
units with authoritative native execution require exact activation.

Keep diagnostic route and explain surfaces side-effect free. They may return a
generated trace identifier for response compatibility, but they do not create a
turn parent or routing decision. Only explicit preflight establishes the durable
request kind and evidence lifecycle that Stop/finalization can close.

Require explicit correlation at public evidence-mutation boundaries. Missing or
ambiguous correlation fails closed rather than fabricating an empty authoritative
state. Stop retries are revalidated and bounded; loop prevention does not bypass
evidence reconciliation.

Persist a content-free request fingerprint, the typed state-aware
classification, and its legacy `trivial` or `nontrivial` request-kind projection
on the turn parent. The database record, not adapter memory, is the authority
when preflight and finalization run in separate host processes. Reject
reuse of an active trace for a different request, close a partially failed
preflight as `preflight_failed`, and never promote migration-created historical
parents into open-turn recovery.

Treat terminal state as monotonic. Evidence validation and mutation occur in the
same write transaction as their insert, while terminal closure uses a
compare-and-set from `active` or `evidence_only`. A later callback may read
immutable historical evidence but cannot reopen the turn or rewrite
`retry_exhausted`, `failed`, or another terminal outcome.

Bound selector signals, detected work units, persisted suggestions, and the
combined preflight context before iterating or writing. Stable planned work-unit
IDs remain canonical when a host returns a different native child/run ID, and a
failed or skipped outcome is sticky for that canonical unit.

Completion enforcement follows real host capabilities. Claude Code retry
exhaustion uses its terminal stop control. OpenClaw provides bounded draft
revision but no permanent denial result at that surface, so ADR-0049 adds an
audited synchronous outbound seal and keeps missing or bypassed delivery hooks
as an explicit host trust boundary. Hermes exposes a bounded `pre_verify` nudge
for code-edit turns but no model-retry
result from its output transform. Its generated plugin catches hook exceptions
and enforces through replacement: only an authoritative accept returns the
finalized draft, while correlation, evidence, policy, persistence, or adapter
failures return a bounded nonempty safe response that prevents the unverified
draft from leaking. Runtime disablement remains an explicit pass-through.

## Consequences

- Current headers describe who shaped the current turn rather than everyone seen
  during the conversation.
- Session history remains complete for audit, analytics, and the dashboard.
- Host adapters must preserve session and trace/turn identifiers through every
  preflight, tool, finalization, and Stop surface.
- Legacy load rows remain visible historically but cannot satisfy current-turn
  enforcement.
- Fresh installations always have a deterministic coordination fallback.
- Diagnostic routing cannot manufacture an open turn or contaminate implicit correlation.
- Each injected turn capsule is bounded and explicitly invalidates earlier
  specialist capsules semantically. Physical transcript retention and
  compaction remain host-owned residual behavior, so total host context is not
  claimed to be independent of session length.
- Separate hook processes enforce the same durable typed classification and its legacy completion-policy projection.
- Concurrent evidence callbacks cannot append after terminal closure.
- Partial isolated activation cannot finalize executed work: every started,
  running, delegated, or completed isolated unit needs its own consumed one-use
  receipt and reciprocal native identity. Planned but unexecuted units close
  truthfully through decline, skip, or bounded retry exhaustion instead of
  becoming fabricated load evidence.
- Historical recommendations remain auditable without being misreported as the
  worker or specialist that actually executed.
- All current MCP-backed isolated executions retain generic delegation
  attribution even when exact capability retrieval and a native tool run are recorded.
- OpenClaw's host registration, equal-priority same-process plugin, and delivery-
  path bypass boundaries remain documented separately from its audited seal.
- Hermes uses one documented `pre_verify` continuation on code-edit turns,
  then relies on mandatory safe output replacement for every turn; the absence
  of a host permanent-deny result remains explicit.

## Alternatives

- Keep one cumulative session set and shorten prompts. Rejected because stale
  evidence would remain semantically incorrect even if it were smaller.
- Delete old load rows after each turn. Rejected because it destroys audit history
  and makes dashboard explanations incomplete.
- Treat missing correlation as an empty turn. Rejected because absence of proof is
  not proof that no specialist was used.
- Choose a single generic CEO fallback. Rejected because the approved policy uses
  separate orchestration and chief-of-staff responsibilities.
- Always add the fallback pair alongside matched specialists. Rejected because it
  spends context and creates instruction pressure when routing already has a match.
- Infer specialist execution from a host-native worker name. Rejected because
  Codex task names, Claude subagent types, OpenClaw agent IDs, and Hermes roles
  identify host workers, not proof that an Agency prompt version was retrieved
  or applied by that worker.
- Require every selected plan reference to activate. Rejected because selection
  is not execution; native hosts may validly merge, skip, or decline planned
  units, and only work they actually run needs an activation receipt.
