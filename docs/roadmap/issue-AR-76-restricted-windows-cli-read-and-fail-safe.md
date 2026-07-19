---
title: "AR-76: Make restricted Windows CLI read-capable and fail-safe"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-17
tags: [operations, cli, windows, security, routing, delegation]
related:
  - docs/decisions/0059-broker-restricted-windows-agent-controls.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-76
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/77"
depends_on: [AR-75]
blocks: []
---

# AR-76: Make restricted Windows CLI read-capable and fail-safe

## Problem

Several CLI surfaces still assume they can construct or mutate the owner-private
SQLite Store from a restricted Windows Codex token. Read-only selector commands
can traceback instead of using a safe read boundary, while delegation, setup,
roster mutations, and config reset can surface raw permission failures.
Delegation must not be proxied through the normal-user dashboard because an
arbitrary backend command would become a privilege-escalation boundary.

## Current state

The implementation now keeps bulk listing on AR-75's compact pages and executes
search, route, explain, and policy inside the authenticated service over one
config-bound routing snapshot. The CLI receives bounded outputs and exact
config/Store/roster identity instead of a full selector catalog. Full-suite and
installed restricted-Codex acceptance remain pending.

## Approach

Keep direct Store access primary. On exact restricted-token Store refusal, use
compact pages only for listing and broker search, route, explain, and policy as
complete read-only server-side operations. Validate bounded result contracts and
the operation's config path/revision, active Store path, and roster revision;
refuse a restart-required Store mismatch. Fail delegation before execution with
a structured diagnostic and no evidence claim. Preflight or contain expected
permission failures for install, configuration setup/reset, and roster
mutations; make any committed partial state explicit. Add a sanitized outer
OS-error boundary as defense in depth.

## Dependencies

AR-75 owns the narrow roster read protocol. ADR-0060 distinguishes safe
read-only brokerage from execution or generic mutation proxying.

## Acceptance

- [x] Restricted search, route, explain, and policy execute server-side over a complete validated routing snapshot.
- [x] Restricted agent and roster list use complete compact pages without bulk selector metadata.
- [x] Restricted delegation fails before execution or evidence fabrication and is never brokered.
- [x] Install/setup, roster mutations, and config reset report controlled truthful failures.
- [x] Config setup never prints complete success before Store and roster initialization.
- [x] Normal direct behavior and Agency-off early bypass remain unchanged.
- [x] Windows-simulated tests and installed restricted-Codex smoke pass.
- [x] Exact coverage, full-suite, tracker, and merged-install gates pass.
