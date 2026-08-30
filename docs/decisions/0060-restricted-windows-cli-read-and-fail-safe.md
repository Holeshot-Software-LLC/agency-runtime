---
title: "Broker restricted CLI reads narrowly and fail unsafe operations before execution"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-17
tags: [operations, cli, windows, security, delegation]
related:
  - docs/roadmap/issue-AR-76-restricted-windows-cli-read-and-fail-safe.md
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/decisions/0059-broker-restricted-windows-agent-controls.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0060
type: decision
deciders: [maintainers]
---

# ADR-0060: Broker restricted CLI reads narrowly and fail unsafe operations before execution

## Context

A restricted Codex token may safely ask the authenticated normal-user dashboard
for bounded roster facts, but it must not use that process as a generic Store,
configuration, network, or command-execution proxy. Uncaught permission errors
are unusable; widening privilege to avoid them is unsafe.

## Decision

Keep direct Store access primary. After an exact
`RestrictedWindowsTokenError`, agent and roster listing may traverse only the
compact revision-stable activation pages defined by ADR-0059. Do not export the
full selector catalog through bulk pages.

For search, route, explain, and policy, broker the complete read-only operation
inside the authenticated dashboard service. The service freezes one
config-bound routing snapshot under the config read lock, verifies that its
active Store still matches the desired configured path, and returns an
operation identity containing the config path/revision, active Store path, and
roster revision. Search returns bounded top-result summaries, route and explain
return the ordinary bounded explanation receipt, and policy returns a
credential-free bounded policy projection plus active slugs. The restricted
client validates that identity and output contract. Never substitute an empty
successful catalog or retry a conflict automatically.

Do not broker delegation or arbitrary backend argv. If Store access is refused,
return a structured failure before backend selection, process creation, or
delegation evidence. Likewise, setup and roster mutations receive explicit
command-specific or outer sanitized OS-error handling; they do not acquire a
generic dashboard write proxy. Configuration setup reports a committed config
as partial state until Store/roster initialization also succeeds.

## Consequences

- Read-only selector CLI remains useful in restricted Codex.
- Full routing metadata remains inside the owner service; the restricted
  process receives only the result required by its command.
- The dashboard cannot be repurposed as a same-user privilege escalation or
  arbitrary execution service.
- Expected permission failures are nonzero diagnostics rather than tracebacks.
- Partial setup state is explicit and recoverable from a normal user shell.

## Alternatives

- Proxy every Store call. Rejected because it erases capability boundaries.
- Proxy delegation. Rejected because generic commands would execute with the
  dashboard user's broader token.
- Return an empty catalog. Rejected because that fabricates successful absence.
- Leave raw tracebacks. Rejected because they are neither usable nor bounded.

## Provenance

`AR-76` records implementation and installed verification; commit provenance is
added after the substantive commit exists.
