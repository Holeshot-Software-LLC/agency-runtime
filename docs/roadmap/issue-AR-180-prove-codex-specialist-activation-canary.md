---
title: "AR-180: Prove Codex specialist activation in the live canary"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, activation, delegation, production-readiness]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/dashboard/dashboard-render.js
  - tests/test_host_canary.py
  - tests/test_codex_activation_canary.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-180
priority: p0
tracker_url: null
depends_on: [AR-143]
blocks: [AR-119]
---

# AR-180: Prove Codex specialist activation in the live canary

## Problem

The current-profile Codex canary requires the expected `code-reviewer` to have
activation evidence, but its prompt forbids all tool use. Codex uses isolated
specialist delivery: selection creates a native delegation plan, while prompt
retrieval and activation occur only at a real native child boundary. The
canary can therefore prove hooks, routing, and finalization without being able
to satisfy its own specialist-activation gate.

## Current state

The local candidate now emits exactly one bounded work unit, uses the Codex
native `spawn_agent`/`wait_agent` surface, and proves the complete hook-to-Store
chain from prompt delivery through accepted parent finalization. Strict proof
binds the JSONL tool call, immutable `native_hook` receipt provenance, one-use
activation consumption, child lifecycle, delegation, model receipt, exact
header, current install identity, and the dedicated
`agency.codex-activation-canary.v1` contract. Schema v38 migrates legacy rows to
manual provenance and rejects impossible origin/tool-ID pairs.

The hook remains advisory to Codex scheduling: it injects or rejects only a
positively identified Agency-owned planned call. Ambiguous and unmatched native
calls return no hook decision. A current-profile recheck clears the older
success immediately before invocation, so a failure or timeout cannot leave a
stale readiness claim. Isolated and tokenless diagnostics never persist this
attestation. The dashboard now labels the record as the last successful proof,
neutralizes it when host inspection expires, and exposes no canary action.

Focused proof, provenance, migration, output-durability, dashboard API, and all
106 dashboard UI tests pass locally. The next gate is one freshly installed,
bounded current-profile invocation without hook-trust bypass. Until that real
run passes, no specialist activation or current attestation is claimed.
Tracker creation remains pending authorization.

## Approach

Define a deterministic, time-bounded Codex activation probe whose requested
work has one safe isolated unit and one eligible specialist. Prove first that
the non-interactive Codex surface exposes the required native delegation tool.
Then require exactly one child launch, exact work-unit correlation, pre-LLM
specialist delivery, one-use activation consumption, child completion, parent
finalization, and a valid response header. Reject absent tools, topology drift,
extra children, timeouts, unconsumed grants, parent-only prompt loading, and
uncorrelated evidence. Keep shell, filesystem writes, external services, and
hook-trust bypass disabled.

## Dependencies

ADR-0077 owns behavioral activation proof. ADR-0104 supplies the exact installed
candidate. The host must expose a non-interactive native-child surface that the
canary can invoke safely; if it does not, activation needs a different attended
probe instead of weakening the evidence gate.

## Acceptance

- [x] The canary request deterministically produces exactly one bounded work unit
  and one expected specialist without semantic-plan fanout.
- [ ] Current-profile Codex exposes and invokes the supported native child tool
  without hook-trust bypass, shell access, file writes, or external services.
- [ ] PreToolUse, SubagentStart, PostToolUse, SubagentStop, and Stop evidence is
  correlated to one session, trace, work unit, child, and install identity.
- [ ] The expected specialist prompt is delivered only to the child and its
  one-use activation grant is consumed exactly once.
- [ ] Child completion and parent finalization are accepted, the Agency header
  is valid, and the installation-bound current-profile attestation persists.
- [x] Missing tools, extra delegation, timeout, drift, replay, or incomplete
  evidence fails and closes only the exact canary run.
- [x] Focused tests cover positive, unavailable-tool, timeout, and correlation-
  failure paths before another live attempt.
