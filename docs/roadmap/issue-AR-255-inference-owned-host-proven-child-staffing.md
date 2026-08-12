---
title: "AR-255: Make native child staffing inference-owned and host-proven"
status: open
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [routing, inference, native-child, codex, evidence, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/child_delivery_evidence.py
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-255
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119, AR-180, AR-252, AR-253]
---

# AR-255: Make native child staffing inference-owned and host-proven

## Problem

The current JIT hook pre-narrows and compatibility-selects child cards in
deterministic local code, including a fail-open branch that can deliver every
candidate. That violates ADR-0118. Separately, the Codex canary can treat an
Agency-authored `specialist_load` row as card-delivery proof even though the
authoritative evidence contract requires an artifact written by the host.

Codex exposes model-authored plaintext `task_name`, but the `message` that can
carry context and exact card hashes is encrypted and opaque to the current hook.
The unvalidated label is not a delivery channel. Remaining a supported host
requires an integrity-bound channel, not a waiver or a relabeled Agency receipt.

## Current state

Runtime checkpoint `7e1b3603` makes inference the only native-child staffing
authority, preserves a valid multi-card result exactly, and fails open unstaffed
when inference is absent or invalid. It also collects Claude's canonical child
artifact inside an allocator-sealed disposable profile and current invocation
window, then passes a sealed one-use capability to canary evaluation. Store
rows, backend mappings, CLI input, caller-created roots, stale copies, and
replays cannot mint that capability.

Implementation and simulation are proven, not installed or live behavior. The
SafeClaude integration uses a test-managed install and fake process runner.
Claude's three prior-candidate artifacts remain historical context only. Codex
0.147 still exposes an opaque inter-agent assignment, so the current adapter
returns `unsupported_opaque_interagent_channel` and lets the host proceed
unstaffed. AR-180 owns exact-install and live proof when an integrity-bound
Codex channel is available.

## Approach

Carry a validated inference decision to the native spawn boundary without
restoring Job B or allowing deterministic code to choose workers. Deterministic
logic may filter hard-ineligible cards, validate hashes and compatibility, and
reject invalid output; it may not rank or replace the inference result. If no
valid inference survives, deliver no card and emit an honest diagnostic.

Make the host-authored child artifact the sole green Rule-4 authority. Agency
Store rows may index or diagnose correlation but cannot prove delivery. Build a
Codex-supported, integrity-bound context channel here; AR-180 exact-installs and
live-proves that channel.

## Dependencies

- ADR-0118 is the selection authority.
- `child_delivery_evidence.py` is the evidence-authority starting point.
- AR-209 is historical provenance for the retired plan-row transport and must
  not be restored as the fix.

## Checkpoint evidence

- Runtime `7e1b3603` and ledger `fb650b04` contain the implementation and its
  required traceability record.
- The final AR-255 focused package passed 229 tests with 1 skipped. The named
  fast Python production spine passed 673 with 6 skipped, dashboard UI passed
  134, and documentation validation passed for 685 Markdown files.
- Ruff lint and format, policy availability, worklog consistency, metadata, and
  `git diff --check` passed.
- Two independent adversarial passes found and drove fixes for Store-only proof,
  caller-selected roots, same-candidate replay, isolated install identity, and
  stale copied artifacts. The final reattack reported no unresolved Critical or
  High finding; its focused child-evidence suite passed 54 tests.
- Same-process private reflection and same-account transcript plus Store
  forgery remain the documented threat-model exclusion. No installed or live
  host layer advances from this checkpoint.

## Acceptance

- [x] Every delivered specialist slug and version is an exact member of one
      validated inference decision; deterministic code never chooses a worker.
- [x] A valid compatible multi-card inference decision reaches the child intact;
      deterministic code does not truncate it to one card.
- [x] No provider or no valid inference yields no Agency-supplied specialist,
      card, activation, or hire and records one explicit failure reason; the
      native host remains free to proceed unstaffed.
- [x] Canary success requires a host-written child artifact containing the
      exact card hashes before the child's first speech; Store-only rows fail.
- [x] Spoofed, replayed, stale, encrypted-but-unbound, or Agency-authored
      evidence cannot produce a green result.
- [ ] The Codex channel binds the inference decision, parent/child correlation,
      card hashes, and install identity; focused spoof, replay, stale, and
      opaque-label adversarial tests pass.
- [ ] Claude's three prior-candidate artifacts remain valid historical
      evidence, an exact-candidate host artifact turns its installed/live
      layers green, and the current projection rejects Store-only claims.
