---
title: "AR-99: Keep dashboard brokerage usable after master control materializes"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [operations, dashboard, windows, security, runtime-control]
related:
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-74-broker-restricted-windows-host-controls.md
  - docs/roadmap/issue-AR-77-validate-brokered-control-transition-receipts.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-99
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/100"
depends_on: []
blocks: []
---

# AR-99: Keep dashboard brokerage usable after master control materializes

## Problem

In an installed restricted Windows Codex process, the dashboard could broker the
first global toggle while the master-control document was absent. Once that
toggle materialized `control.json`, the service read its own authoritative file
through the sandbox-consumer boundary. Because the service legitimately has
mutation rights, that boundary rejected it and subsequent authenticated runtime
and host-control requests returned HTTP 400.

## Current state

The installed service reproduced the failure while remaining active, reachable,
and authenticated. The strict owner-side reader validates the same durable
document successfully. The server-bound correction and installed off/on
regression are in progress; the master state is currently enabled.

## Approach

Keep untrusted or restricted host consumers on the existing reduced-privilege,
fail-enabled reader. At the authenticated dashboard broker boundary, read the
broker-owned master document through the existing strict owner-side validator.
Do not weaken path, ACL, schema, generation, confirmation, authentication, or
transition-receipt validation.

## Dependencies

AR-57 defines the durable master switch, AR-74 defines the authenticated
restricted-Windows brokerage boundary, and AR-77 requires exact transition
receipts. The correction can be verified independently. ADR-0058 constrains the
dashboard to narrow authenticated operations rather than a generic privilege
proxy.

## Acceptance

- [ ] The authenticated dashboard reads its authoritative master document through the strict boundary.
- [ ] Restricted host consumers remain fail-enabled and cannot forge disabled state.
- [ ] Installed global off then on succeeds after `control.json` exists.
- [ ] Generation CAS and transition-receipt validation remain exact.
- [ ] Focused security review, full suite, rebuilt artifact, and installed Codex smoke pass.
