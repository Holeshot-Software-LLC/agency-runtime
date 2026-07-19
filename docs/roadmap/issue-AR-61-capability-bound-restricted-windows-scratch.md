---
title: "AR-61: Provide capability-bound scratch under restricted Windows hosts"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, windows, portability, delegation, testing]
related:
  - docs/decisions/0056-capability-bound-restricted-windows-scratch.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0052-require-trusted-parents-for-sqlite-store-paths.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-61
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/62"
depends_on: [AR-56, AR-60]
blocks: []
---

# AR-61: Provide capability-bound scratch under restricted Windows hosts

## Problem

A restricted Windows host token can be unable to create or repair the normal
owner-private `~/.agency-runtime` scratch hierarchy. Falling back to the
repository or ambient temporary storage is unsafe when another account can
replace worktrees, process scratch, or test state. This prevented delegation
and even warning-strict pytest startup in the real Codex Windows sandbox.

## Current state

Unrestricted hosts continue to use the normal per-user runtime root. A
restricted Codex process instead discovers a bounded host-owned capability
inside the user-private Codex visualization namespace. It accepts only one
canonical leaf whose owner, ancestor chain, current restricting-SID access,
mutation rights, and open file identity all verify. It creates a new ephemeral
child with a protected DACL for the current user, authoritative logon SID, and
Windows system account. Arbitrary restricting SIDs never become globally
trusted principals. Each launched child independently reattests only its exact
randomized thread-bound allocation, canonical host marker, fixed-depth
root/parent identities, DACL, and effective-token mutation rights; parent
process-local authority cannot cross `exec`. The broadly writable repository
fallback remains forbidden.

## Approach

Use the effective Windows token, preferring a thread token, and accept a logon
SID only when `TokenLogonSid`, enabled `TokenGroups`, and enabled
`TokenRestrictedSids` agree. Resolve the exact current Codex task root first;
for nested Codex workers, perform a capped scan of only the owner-private
visualization namespace and require exactly one leaf bound to a current
restricting capability and proven mutation access. Pin the leaf's canonical
path and file identity, create each child atomically with its protected DACL,
and retain identity receipts through cleanup. Use the same facility for
delegation worktrees, child-process `TEMP`/`TMP`, and restricted-host tests.

Cleanup must remain link-safe and handle Windows read-only Git artifacts.
Unknown, missing, ambiguous, replaced, or stale capabilities fail closed.

## Dependencies

AR-56 established trusted storage-parent requirements, and AR-60 freezes
executable identity before launch. ADR-0039 still forbids repairing an existing
owner-only DACL from a restricted token; this item creates a new protected
ephemeral object atomically instead.

## Acceptance

- [x] Exact logon identity is derived from the effective token and corroborated across all three token views.
- [x] Arbitrary restricted SIDs are never added to the global trusted-principal set.
- [x] The repository and ambiguous or broadly writable scratch roots remain rejected.
- [x] Root and nested Codex tasks can allocate, use, identity-check, and remove private scratch without escalation.
- [x] Delegated child `TEMP`/`TMP` and real Git worktrees use the capability-bound root.
- [x] Windows read-only Git artifacts are cleaned without following links or deleting outside the receipt.
- [x] Store-backed tests under the restricted scratch root pass the normal parent-trust checks.
- [x] Every child independently reattests its exact thread-bound allocation after `exec`.
- [x] Windows and Linux portability tests preserve the unrestricted-host path.
