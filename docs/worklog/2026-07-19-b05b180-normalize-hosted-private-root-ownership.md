---
title: "Normalize hosted Windows private root ownership"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [windows, security, ci, portability, coverage]
related:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0056-capability-bound-restricted-windows-scratch.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: b05b180
short: b05b180
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Normalize hosted Windows private root ownership

## Purpose

Accept Windows' textual canonicalization of an atomically created private-root
owner without trusting a shared administrator, system, or token-owner group,
and restore the hosted Ubuntu quality job to deterministic 100% branch
coverage.

## Approach

Parse the captured SDDL and the exact current `TokenUser` SID through native
Windows APIs, then compare their binary identities with `EqualSid`. The final
private root now requires that exact identity even when Windows renders it as a
well-known alias such as `LA`. Administrator, LocalSystem, TrustedInstaller,
pseudo-owner, arbitrary group, malformed, NUL-tainted, and null native results
remain rejected.

Keep the existing system-owner classifier as a compatibility API, but remove it
from final-root authorization. Preserve protected/private DACL enforcement and
fail closed when parsing, matching, or native marshalling fails.

Add portable fake-Windows tests for native SID allocation and cleanup, Windows
lock APIs, executable discovery, storage races, dashboard launcher drift, and
the platform branches that an Ubuntu-only coverage job must still prove.

## Challenges encountered

Accepting the process token's default owner was rejected during adversarial
review because `TokenOwner` may be a shared owner-eligible group whose members
retain implicit DACL authority. Binary equality with `TokenUser` resolves only
the representational alias problem and avoids that privilege expansion.

An initial exhaustive local coverage invocation deliberately failed when its
temporary root was forced beneath a shared system temporary directory; the
runtime correctly rejected that namespace. The corrected host-private
invocation exceeded the 20-minute local command ceiling without a final report,
so it is not recorded as a pass. Hosted Ubuntu remains the authoritative
exhaustive coverage gate.

## Decisions and alternatives

- Do not trust arbitrary `TokenOwner` values or privileged groups.
- Do not mutate or repair a foreign-owned pre-existing root.
- Do not compare SDDL owner strings directly when Windows may render the same
  SID using a well-known alias.
- Do not weaken, omit, or aggregate the 100% line-and-branch coverage gate.
- Retain the exported classifier for compatibility, while documenting that it
  is insufficient authorization for a private final root.

## Verification

- `573 passed, 6 skipped` across the affected Windows ACL, private-path,
  executable, lock, storage, dashboard, and portable coverage tests.
- An unrestricted local Windows CI-runtime bootstrap completed successfully.
- Native Windows SID parsing accepted `O:SY` only for `S-1-5-18` and rejected a
  different principal.
- Repository-wide Ruff check, Ruff format check, and `git diff --check` passed.
- Independent security and senior-code reviews reported no remaining
  actionable findings.

## Follow-ups

Run the full hosted Windows and Linux matrix for PR #104. Treat the hosted
Windows bootstrap result and Ubuntu 100% coverage report as the completion
authority for AR-104.
