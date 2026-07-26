---
title: "AR-143: Require genuine operator presence for persistent controls"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [security, dashboard, browser, cli, controls, user-presence]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-actions.js
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-143
priority: p0
tracker_url: null
depends_on: [AR-128]
blocks: []
---

# AR-143: Require genuine operator presence for persistent controls

## Problem

The in-app Browser is model-callable and can operate an existing authenticated
dashboard session. The owner bearer, deterministic confirmation modal, and
generation CAS therefore do not prove a human operator intended a persistent
mutation. Restricted CLI behavior is also an ACL/error outcome rather than one
uniform caller-attestation boundary.

## Current state

AR-128 makes MCP and the restricted dashboard broker read-only, which removes
their direct confused-deputy authority. The owner dashboard still authorizes
configuration, trimming, roster, host, agent, master-control, workforce, and
hiring mutations. Browser automation can read the displayed confirmation,
submit it with the already-loaded owner token, and persist the change.

## Approach

Make the dashboard read-only and reject every mutation endpoint for both owner
and broker bearers. Preserve monitoring and diagnostic value without implying
that a modal is user presence. Audit every CLI and host-native mutation entry
under model-facing identities. Do not restore remote or browser mutations until
an OS-backed, short-lived, single-use operator-presence capability is bound to
the exact method, target, payload digest, generation, and expiry and consumed
atomically.

## Dependencies

AR-128 remains the read-only MCP/broker foundation. ADR-0096 supersedes the
dashboard exception in ADR-0090.

## Acceptance

- Every dashboard mutation rejects owner and broker bearers without state change.
- Authenticated browser automation cannot complete a persistent mutation.
- Every CLI and host-native mutation entry fails closed for a model-facing identity.
- Positive mutations remain only behind a positively attested operator boundary.
- Any future presence capability rejects missing, expired, replayed, target,
  payload, and generation mismatches and succeeds exactly once.
