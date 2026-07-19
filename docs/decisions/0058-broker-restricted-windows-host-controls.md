---
title: "Broker restricted Windows host controls through the authenticated dashboard"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-17
tags: [operations, cli, dashboard, windows, security]
related:
  - docs/roadmap/issue-AR-74-broker-restricted-windows-host-controls.md
  - docs/roadmap/issue-AR-75-broker-restricted-windows-agent-controls.md
  - docs/roadmap/issue-AR-77-validate-brokered-control-transition-receipts.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0057-generation-checked-host-control-mutations.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0058
type: decision
deciders: [maintainers]
---

# ADR-0058: Broker restricted Windows host controls through the authenticated dashboard

## Context

A restricted Windows host token may read and execute installed Agency code but
must not repair owner-only SQLite directory ACLs. That fail-closed rule is
correct, yet a CLI status or soft-control command should not crash when the
normal user dashboard service already owns the Store and exposes the same
bounded operation behind an owner-private descriptor and loopback bearer token.

Making every Store error a remote fallback would hide corruption and could
change normal-shell semantics. Treating a dashboard response as trusted without
validation would also move the failure boundary rather than close it.

## Decision

Use direct Store access for host status and soft control in normal user shells.
Only the exact restricted-Windows-token refusal may switch these CLI operations
to the authenticated dashboard broker. Native host lifecycle never uses this
fallback.

Read status through the dashboard host endpoint. Apply soft control only after
reading the current host generation, then submit the existing exact confirmation
phrase and compare-and-swap generation to the dashboard toggle endpoint. Dry
runs read and project state without mutation. Multi-host operations broker each
requested host independently and preserve partial failures.

Bind every Store-backed host response to the service's canonical config path
and revision, environment-override names, active Store path, desired configured
Store path, and restart-required state. The restricted client requires that
identity to match its default installed config and Store environment. If the
service's already-open Store differs from the desired configured path, reject
status and mutation until the service restarts; never combine new config policy
with old SQLite state. Serialize host mutations against config writers while
rechecking this binding.

Treat broker output as protocol input: require one bounded mapping, an allowlisted
host slug, exact requested-host identity, JSON booleans for state, non-boolean
non-negative integers for generations, and the expected success/status shape.
Reject duplicate hosts, mismatched state, stale generations, malformed payloads,
authentication failure, and unavailable service with sanitized nonzero CLI
output. Never fall back from a broker failure to an unsafe local mutation.

## Consequences

- Installed Codex can use status and host soft controls without granting its
  restricted token permission to rewrite Store ACLs.
- The normal CLI path remains local and does not acquire a dashboard dependency.
- Dashboard absence is an explicit operational failure, not a traceback or a
  silently fabricated default state.
- Store-path changes are explicit restart boundaries rather than implicit
  redirection of a live service.
- Global and host controls share one least-privilege brokerage pattern while
  retaining separate documents, generations, and semantics.
- New restricted-process Store operations must be reviewed individually; this
  decision does not authorize a generic Store proxy.

## Alternatives

- Relax Store ACL enforcement for restricted Codex. Rejected because status
  does not justify granting or simulating mutation authority.
- Always route CLI host controls through the dashboard. Rejected because normal
  shells should not depend on a background service.
- Catch every Store exception and broker it. Rejected because corruption,
  identity drift, and schema failures must remain visible.
- Report default enabled values without a Store. Rejected because fabricated
  status would violate evidence fidelity and could overwrite a real generation.

## Provenance

`AR-74` records implementation and installed restricted-Codex verification.
The implementation commit will be linked through the roadmap and worklog after
it exists.
