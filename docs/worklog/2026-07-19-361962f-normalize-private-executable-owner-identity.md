---
title: "Normalize private executable owner identity"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [windows, security, ci, portability]
related:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0056-capability-bound-restricted-windows-scratch.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 361962f
short: 361962f
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Normalize private executable owner identity

## Purpose

Allow a private executable copied into the hosted Windows runtime to pass
artifact validation when Windows renders its owner as a well-known SDDL alias,
without widening trust to a shared account or group.

## Approach

Apply the existing native SID comparison used for private directories to
executable files. The validator parses the captured owner and compares it to
the exact current `TokenUser` SID with `EqualSid`; textual equality remains the
fast path, and LocalSystem, Administrators, and TrustedInstaller remain the
only separately enumerated system owners supported for executable artifacts.

Expose the owner matcher as a keyword-only test seam. Any read, parse, or match
failure remains fail-closed.

## Challenges encountered

The preceding hosted Windows run proved that private-root creation was fixed,
then failed at the next trust boundary while snapshotting the copied
`node.exe`. The file validator still compared the SDDL owner text directly, so
the same principal expressed as `LA` and as a numeric current-user SID was
incorrectly treated as cross-account mutation risk.

## Decisions and alternatives

- Reuse exact binary `TokenUser` equality instead of adding `LA` to a trusted
  alias list.
- Preserve the fixed system-owner allowlist for legitimately system-installed
  executable artifacts.
- Reject matcher exceptions instead of falling back to textual alias trust.
- Keep all DACL mutation-right checks unchanged.

## Verification

- `164 passed` across Windows ACL, subprocess authority, portable ACL coverage,
  and CI-runtime preparation tests.
- Ruff check and format checks passed for the changed files.
- `git diff --check` passed.
- A native Windows `scripts.prepare_ci_runtime` smoke created, copied, and
  verified a private `node.exe` successfully.

## Follow-ups

Confirm the hosted Windows matrix passes at this commit and keep Ubuntu's 100%
line-and-branch coverage job authoritative for AR-104 completion.
