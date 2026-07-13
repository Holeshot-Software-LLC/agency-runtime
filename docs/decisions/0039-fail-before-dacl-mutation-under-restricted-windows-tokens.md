---
title: "Fail before DACL mutation under restricted Windows tokens"
status: accepted
category: decisions
created: 2026-07-12
updated: 2026-07-12
tags: [security, windows, permissions, portability]
related:
  - docs/THREAT_MODEL.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0039
type: decision
deciders: [maintainers]
---

# ADR-0039: Fail before DACL mutation under restricted Windows tokens

## Context

Configuration, SQLite state, dashboard descriptors, and temporary canary
credentials require owner-private permissions. A Windows restricted token can
identify the account owner yet be unable to use that owner's allow entry during
the restricted access check. Replacing a directory DACL with an owner-only ACL
from such a process can therefore succeed and immediately make the directory
inaccessible to the process that changed it.

Silently retaining inherited permissions would keep the process running but
would make the privacy claim false. Mutating first and detecting failure later
can strand files or lose the ability to restore the prior descriptor.

## Decision

Use one shared native Windows ACL implementation. First inspect the existing
owner and DACL without mutation. An exact owner-only protected ACL, or an exact
owner-only ACL inherited from a recursively verified private parent, already
satisfies the postcondition and is left untouched. Otherwise open and inspect
the current process token before any permission or DACL mutation. If the token
is restricted or its restriction state cannot be proven, raise a stable
security error and do not call the DACL mutation APIs or perform a preparatory
chmod. Configuration, storage, and canary boundaries translate that error
without weakening their owner-private postcondition; partial canary credential
destinations are removed.

## Consequences

- Codex or another sandboxed process cannot lock itself out by replacing an ACL
  it cannot subsequently use.
- Existing bytes and permissions remain unchanged when the precondition fails.
- Repeated construction does not rewrite an already-private DACL, reducing
  Windows startup overhead and allowing safe inspection from restricted hosts.
- A restricted host must rerun the operation from an unrestricted user process
  or use a separately reviewed private-storage mechanism.
- Permission setup can fail earlier, but it now fails truthfully and
  reversibly.

## Alternatives

- **Add sandbox capability SIDs to every DACL.** Rejected because capability
  identities and sharing semantics vary by host and can broaden access beyond
  the owner-only contract.
- **Keep inherited ACLs for restricted tokens.** Rejected because the runtime
  could no longer claim that sensitive state is private.
- **Apply the ACL and roll it back after an access test.** Rejected because a
  failed access check can also prevent reliable rollback and cleanup.
