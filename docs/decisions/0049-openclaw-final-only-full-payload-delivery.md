---
title: "Require final-only full-payload delivery on OpenClaw"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-08-22
tags: [openclaw, finalization, streaming, security, host-integration]
related:
  - docs/roadmap/issue-AR-33-openclaw-final-outbound-seal.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0049
type: decision
deciders: [maintainers]
---

# ADR-0049: Require final-only full-payload delivery on OpenClaw

## Context

OpenClaw exposes a model-finalization hook that can ask for a bounded revision,
but revision is not the same operation as denying a payload at the delivery
boundary. Its configured channels can stream previews or blocks, and an
outbound reply can contain visible text, spoken text, TTS supplements, media,
or channel-specific data. Validating only one string does not prove that the
payload delivered later is the payload Agency accepted.

OpenClaw plugins run in one process and share modifying-hook priority. A bridge
that waits asynchronously can lose its host deadline, while an unbounded range
of future host releases or an untrusted later plugin can invalidate assumptions
about ordering and dispatch coverage.

## Decision

Treat final-only delivery configuration as part of the native OpenClaw safety
contract. Before plugin mutation, require an audited stable release line, prove
the gateway is stopped, and inspect every required hook. Use the OpenClaw CLI as
the sole configuration writer. Disable configured preview and block streaming
leaves transactionally, retain only their prior values and container presence,
bind the integrity-protected backup to the effective profile/config identity,
and verify both application and compensation. Do not restore streaming merely
because Agency's soft runtime control is off; restoration is safe only after
plugin disablement or absence is proven.

Make the last reply-payload hook a synchronous, bounded authorization gate. It
canonicalizes the complete payload with byte, depth, and node ceilings, requires
all present policy-text surfaces to agree, and binds the outbound payload hash
separately from the policy-text hash committed with the terminal turn. Missing
trace recovery may select the latest exact accepted terminal turn only when no
open turn or retirement barrier makes that recovery unsafe.

After exact authorization, add a random one-use invisible marker to visible
text or a marker-only carrier for spoken/media delivery. The last message hook
consumes and removes it. A grant is bound to session, turn, payload, kind, and
marker, expires quickly, and cannot authorize a concurrent same-text response.
An enabled payload without policy text is denied. Explicit runtime disablement
passes through truthfully using the same dispatch carrier where the host needs
one to reach the stripping hook.

An accepted finalizer tool result is not channel delivery. A silent sentinel
emitted after that result is a failed delivery outcome even when the Store turn
is complete; it cannot substitute for the exact authorized payload reaching
the host-owned outbound path.

Use the lowest JavaScript priority value for both modifying hooks and treat
other same-process plugins as trusted code. The installer proves registration
and required hook availability, not arbitrary third-party delivery behavior.
Qualify later OpenClaw release lines deliberately rather than assuming forward
compatibility from a version comparison.

## Consequences

- Invalid or unverifiable final replies are cancelled at outbound delivery even
  after OpenClaw's model-revision budget is exhausted.
- Partial streaming cannot publish before terminal evidence while the managed
  integration is installed.
- Text, speech, TTS, media metadata, and channel data are bound as one payload;
  one string cannot stand in for a different outward response.
- Configuration changes are reversible without copying credentials or unrelated
  OpenClaw settings into Agency state.
- Soft disablement does not silently re-enable streaming and does not invent
  Agency evidence.
- A new OpenClaw release line remains unsupported until its hook order and
  dispatch behavior are reviewed and the qualification gate is updated.
- A malicious same-process plugin, a plugin loaded after Agency with an equally
  terminal priority, or a host that omits the registered hooks remains outside
  the in-process enforcement boundary and must not be described as verified.

## Alternatives

- Rely on `before_agent_finalize` revision alone. Rejected because its bounded
  retry result cannot permanently deny the later outbound payload.
- Hash only the rendered header text. Rejected because media and channel data
  could change while the text remains identical.
- Rewrite the full OpenClaw configuration file. Rejected because it expands the
  credential and concurrent-update boundary beyond owned streaming leaves.
- Restore prior streaming settings whenever Agency is toggled off. Rejected
  because the still-loaded plugin and an in-flight turn could then observe
  partial delivery.
- Accept every later stable OpenClaw version. Rejected because version ordering
  is not evidence that modifying-hook and channel-delivery semantics stayed the
  same.
