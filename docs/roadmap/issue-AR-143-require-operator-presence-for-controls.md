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
  - agency_runtime/core/operator_presence.py
  - agency_runtime/cli/main.py
  - agency_runtime/cli/roster_commands.py
  - agency_runtime/core/store/roster.py
  - tests/test_cli_operator_presence.py
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

The original owner-dashboard vulnerability is now fail-closed: the shipped
browser has no mutation client and every former endpoint rejects both owner and
broker bearers without dispatch. One CLI pre-dispatch guard covers every
persistent mutation family, but its production OS verifier deliberately returns
unavailable. The product therefore has safe read-only operation and no positive
persistent setup/control path yet.

## Approach

Make the dashboard read-only and reject every mutation endpoint for both owner
and broker bearers. Preserve monitoring and diagnostic value without implying
that a modal is user presence. Audit every CLI and host-native mutation entry
under model-facing identities. A positive CLI path must prepare its exact
authoritative mutation before verification, seal the method, resolved resource
identity, payload binding, and every applicable revision/CAS token, obtain one
native verification result, revalidate the sealed state inside the mutation
lock, and commit through the same resource owner exactly once. Its trusted
native prompt must show a bounded human-readable action, exact target,
current-to-target transition, and material consequence. The direct verifier
result is consumed synchronously in that call stack and is never exported as an
authorization bearer.
Deferred input must be read into the prepared mutation before verification.
Secret-bearing payloads must be bound internally without exporting a stable
secret-dependent digest that becomes an offline guessing oracle; the prompt
shows secret presence and effect, never the secret value.
If a future design introduces a transferable capability, it must additionally
be short-lived, audience-bound, single-use, and atomically replay-protected.

## Dependencies

AR-128 remains the read-only MCP/broker foundation. ADR-0096 supersedes the
dashboard exception in ADR-0090.

## Acceptance

- Every dashboard mutation rejects owner and broker bearers without state change.
- Authenticated browser automation cannot complete a persistent mutation.
- Every CLI and host-native mutation entry fails closed for a model-facing identity.
- Positive mutations remain only behind a positively attested operator boundary.
- The positive path prepares before verification and rejects resource, target,
  payload, or applicable revision/CAS changes inside the committing boundary.
- The trusted native prompt makes the exact action, target, current-to-target
  transition, and material consequence intelligible without decoding a digest.
- Deferred stdin/prompt input is prepared before verification, and secret
  payload binding exposes neither the value nor a deterministic guessing oracle.
- A direct native result is consumed once in the same call stack; any future
  transferable capability also rejects missing, expired, replayed, and
  audience-mismatched use atomically.

## Implementation evidence

The dashboard JavaScript contains no mutation client or actionable mutation
controls, and every former mutation endpoint rejects both owner and broker
bearers without dispatch. A single CLI pre-dispatch guard covers every
persistent mutation family and binds a deterministic digest of the parsed
namespace, then rechecks that namespace immediately before handler dispatch.
It does not yet prepare the authoritative mutation, freeze the Store identity,
or bind resolved target state and generation inside the committing
transaction. The verifier call is synchronous, but the returned
`OperatorPresenceReceipt` is merely a constructible informational Python value,
is discarded by the CLI, and must never authorize a commit. Current tests cover
unavailable/cancelled results and namespace mutation—not expiry or replay of a
bearer capability. The current prompt also exposes only command/family/digest,
not the resolved transition needed for informed approval.

The current digest is not safe to reuse as the positive authority contract:
positional low-entropy secrets form an unkeyed offline-guessable commitment,
while `--stdin` and interactive prompt values are read only after the guard and
are not bound at all. Because the verifier remains unavailable, this creates no
positive mutation path today; the prepared-mutation redesign must close both
gaps before enabling one.

Windows SDK inspection and a no-UI activation-factory probe confirm that
Windows 11 exposes a desktop path through
`IUserConsentVerifierInterop::RequestVerificationForWindowAsync`, but it needs
an active app-owned HWND. A draft ctypes backend was rejected before commit:
its callback lifetime could outlive Python pins and its timeout cleanup could
close a still-running async operation. AR-143 therefore remains a production
blocker. The production verifier is deliberately unavailable/fail-closed, no
positive mutation is enabled, and no credential-returning or model-bypass
substitute is accepted. `agency roster rollback` is the first planned prepared
mutation because its Store transaction already enforces version/hash CAS. Its
prepared binding must include Store identity, roster generation, current
version/hash, target version/hash, and target activation-authority evidence.
