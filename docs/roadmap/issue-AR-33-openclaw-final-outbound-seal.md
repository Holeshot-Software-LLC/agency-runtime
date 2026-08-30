---
title: "AR-33: Seal OpenClaw final outbound delivery"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [openclaw, finalization, streaming, security, portability]
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-33
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/34"
depends_on:
  - AR-25
  - AR-27
blocks: []
---

# AR-33: Seal OpenClaw final outbound delivery

## Problem

OpenClaw's model-finalization hook can request a bounded revision, but that
surface alone does not permanently deny an invalid answer. Preview and block
streaming can also publish content before terminal Agency evidence exists. A
missing or already-terminal trace could therefore enter a Stop-style retry
loop, while an asynchronous bridge timeout or a same-text concurrent dispatch
could separate the response that was validated from the payload actually sent.

## Current state

The generated plugin translates preflight, tool, and finalization events, but a
revision result is not an outbound authorization. OpenClaw configurations vary
by profile, state directory, channel, and account, and some channels expose
spoken or TTS surfaces in addition to visible text. Host registration evidence
also proves only that hook names loaded; it does not prove future host releases
retain the audited delivery semantics.

## Approach

Qualify an explicit audited OpenClaw release line and require every load-bearing
hook before installing. With the gateway proven stopped, use only OpenClaw's CLI
to transactionally force final-only delivery for configured agents, channels,
and accounts. Retain an owner-private, values-only backup bound to the effective
profile, state directory, and config path; verify every mutation and rollback.

At runtime, canonicalize and hash the complete outbound payload separately from
the policy text evaluated by Agency. Revalidate and commit the latest exact
turn synchronously in `reply_payload_sending`, then attach a random one-use
dispatch marker. The final `message_sending` hook consumes and strips that
marker so concurrent identical replies, stale grants, and replay cannot cross
authorize one another. Require every present visible, spoken, and TTS text
surface to agree. Allow only the audited `final` and `tool` outbound kinds;
unknown or future partial kinds fail closed instead of being treated as tools.
Deny enabled pure-media output because it has no auditable
header; explicit soft disable remains a truthful pass-through. Keep same-process
plugins inside the trusted host boundary and reject unaudited host release
lines until their delivery contract is requalified.

## Dependencies

AR-25 supplies turn-scoped correlation and AR-27 supplies monotonic retry and
terminal evidence. ADR-0049 governs the OpenClaw-specific configuration,
capability, payload-binding, and residual trust boundaries.

## Acceptance

- [x] Installation fails before mutation when the OpenClaw version or required hook contract is unproven.
- [x] Final-only streaming configuration is transactional, idempotent, profile-bound, and reversible on Windows and Linux.
- [x] The complete outbound payload and evaluated policy text have separate durable hashes.
- [x] Missing trace recovery selects only the latest exact terminal turn and cannot resurrect an open or retired turn.
- [x] Final dispatch authorization is synchronous, bounded, one-use, and exact-payload bound.
- [x] Visible, spoken, TTS, control, and same-text concurrent dispatch paths are adversarially covered.
- [x] Unknown and partial outbound kinds fail closed under an explicit audited-kind allowlist.
- [x] Enabled pure-media output fails closed while explicit runtime disablement remains pass-through.
- [x] The deterministic supported-version harness proves registration, loading, final-only configuration, and outbound behavior without claiming an absent live host.
- [x] Full Windows/Linux exact coverage, package, CI, merge, and tracker reconciliation pass.
