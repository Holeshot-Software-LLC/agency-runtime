---
title: "AR-73: Require private identity-stable custom policy files"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, routing, policy, filesystem, windows, linux]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-73
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/74"
depends_on: []
blocks: [AR-92]
---

# AR-73: Require private identity-stable custom policy files

## Problem

Custom companion-policy loading rejected linked path components and untrusted
parent namespaces, but it did not prove that the policy file itself was owned by
the current user, mutation-safe, or single-linked. A foreign-owned or
cross-account-writable regular file in a trusted directory, or a hard-linked
file mutable through another name, could therefore influence agent selection.

## Current state

Policy reads are bounded, YAML parsing is bounded, parent namespaces are checked,
path components reject symlinks and reparse points, and the file identity is
compared before and after the read. The missing control is privacy and unique
linkage of the present file itself. An absent custom policy contains no external
content and safely falls back to the bundled policy while remaining visible on
the next identity probe.

## Approach

Before consuming a present policy, require one regular non-link file with a
single link, current-user ownership, and permissions/DACLs that prevent another
account from mutating it. Bind validation and bounded reading to stable native
file identity, then confirm the path identity after the read. Keep Windows and
POSIX behavior fail closed and preserve the absent-policy cache performance.

## Dependencies

ADR-0006 defines config-first policy resolution and ADR-0021 defines companion
policy semantics. This issue tightens the filesystem trust boundary without
changing routing precedence or fallback behavior.

## Acceptance

- [x] Present custom policies require one regular non-link file with exactly one link.
- [x] POSIX policies require current-user ownership and no group/other mutation rights.
- [x] Windows policies require a current-user mutation-safe file DACL.
- [x] Validation, bounded read, and post-read identity checks reject swaps and hard-link attacks.
- [x] Absent policies remain fast, bundled-only, and detect newly appearing files on the next call.
- [x] Focused POSIX, Windows-simulated, race, namespace, and performance regressions pass.
- [x] Exact coverage, full-suite, installed-smoke, tracker, and merged-install gates pass.
