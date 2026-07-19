---
title: "Use capability-bound ephemeral scratch for restricted Windows hosts"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-16
tags: [security, windows, portability, delegation, filesystem]
related:
  - docs/roadmap/issue-AR-61-capability-bound-restricted-windows-scratch.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0052-require-trusted-parents-for-sqlite-store-paths.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0056
type: decision
deciders: [maintainers]
---

# ADR-0056: Use capability-bound ephemeral scratch for restricted Windows hosts

## Context

Agency Runtime requires private temporary directories for delegated child
processes, isolated Git worktrees, and tests. On a normal user token, an
owner-private directory below `~/.agency-runtime` supplies that boundary. The
real Codex Windows sandbox uses a restricted token that can read the user's
home but cannot safely create or repair that owner-only hierarchy.

The repository is not a safe substitute when its DACL permits Authenticated
Users to mutate or delete children. Ambient temporary directories can carry
host capability grants that are not globally trustworthy. A random directory
name, raw environment path, or arbitrary SID from `TokenRestrictedSids` does
not prove a private boundary. Windows 11 POSIX rename semantics also mean a
no-delete-share directory handle alone is not a complete substitution defense.

## Decision

Keep the normal owner-private per-user runtime root for unrestricted Windows
and POSIX hosts. For a restricted Codex Windows token, accept only a
session-scoped host capability inside the canonical, current-user-owned Codex
visualization namespace. Resolve the current task UUID directly when its leaf
exists. Nested workers may use a bounded scan of that namespace only when
exactly one leaf satisfies every owner, parent-chain, ACL, current-token
capability, mutation-access, canonical-path, non-reparse, and file-identity
check. Zero or multiple candidates fail closed.

Inspect the effective token, preferring an impersonating thread token and
falling back to the process token only when the thread has no token. Treat a
logon SID as authoritative only when `TokenLogonSid`, an enabled
`SE_GROUP_LOGON_ID` entry in `TokenGroups`, and an enabled entry in
`TokenRestrictedSids` all identify the same SID. Never promote other
restricting SIDs into the global trusted-principal set.

Create each ephemeral child atomically with a protected DACL granting the
required rights only to the current user, the authoritative logon SID, and
Windows system administration principals. Bind the accepted host leaf and
child to open-handle/canonical-path/file-ID receipts, revalidate identity at
handoff and cleanup, and fail closed on replacement. Cleanup is bounded to the
received identity, does not traverse links or reparse points, and explicitly
handles read-only Git artifacts. Worktrees never fall back into an
Authenticated-Users-writable repository.

A process-local capability receipt is not transferable authority across
`exec`. Name each allocation with a randomized thread-bound identity and a
canonical package-owned host marker. Every child independently reattests only
that exact allocation: the visualization root, task parent, marker, lexical and
resolved file identities, DACL, effective-token mutation access, and fixed path
depth must all match. A renamed allocation, a sibling with a similar name, or a
parent receipt without child proof fails closed.

## Consequences

- Restricted Codex root and nested worker processes can use delegation and run
  the production test gate without elevating or weakening repository ACLs.
- Claude Code, Hermes, OpenClaw, Linux, and unrestricted Codex processes retain
  the portable normal per-user path and do not depend on Codex directories.
- The capability is ephemeral. A changed logon SID, missing host namespace, or
  ambiguous eligible leaf requires fresh host state and fails closed.
- Parent and child process authority remain separately evidenced, so a valid
  parent lookup cannot be replayed by an unrelated child after `exec`.
- File-identity receipts detect substitution but do not isolate mutually
  hostile processes sharing the same operating-system account and logon. The
  threat model already treats same-account control as trusted; stronger
  isolation would require a separate broker or token.
- Repository DACL weakness remains visible as a host property and never becomes
  evidence that the repository is a private scratch root.

## Alternatives

- Fall back to a directory inside the repository. Rejected because a broad
  repository DACL permits cross-account substitution and also exposes `.git`.
- Trust every SID in `TokenRestrictedSids`. Rejected because Windows permits
  arbitrary shared groups as restricting SIDs.
- Trust `%TEMP%` or a raw host-provided path. Rejected without the complete
  owner, ancestor, ACL, access, and file-identity proof.
- Rely only on a handle opened without `FILE_SHARE_DELETE`. Rejected because
  live Windows 11 POSIX rename behavior can still move the directory.
- Require an installed unrestricted broker. Deferred as a higher-assurance
  option; it would add service lifecycle and authenticated IPC complexity that
  the current same-account threat model does not require.
