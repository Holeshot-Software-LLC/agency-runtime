---
title: "AR-108: Make owned process containment atomic and session-escape resistant"
status: done
category: roadmap
created: 2026-07-19
updated: 2026-07-20
tags: [security, processes, delegation, windows, linux, portability]
related:
  - agency_runtime/core/owned_process.py
  - agency_runtime/core/owned_process_capture.py
  - agency_runtime/core/owned_process_linux.py
  - agency_runtime/core/owned_process_windows.py
  - agency_runtime/core/owned_process_windows_atomic.py
  - agency_runtime/core/delegation/backend_process.py
  - agency_runtime/core/delegation/backend_process_compat.py
  - scripts/release_git.py
  - docs/THREAT_MODEL.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-108
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/110"
depends_on: []
blocks:
  - AR-107
---

# AR-108: Make owned process containment atomic and session-escape resistant

## Problem

An argument-array launch, bounded streams, and a trusted executable do not by
themselves prove ownership of the whole process tree. The prior Windows path
created the child suspended, but launcher death before post-creation Job Object
assignment could leave that child outside the kill-on-close ownership boundary.
A POSIX descendant can separately escape a process group by starting a new
session or double-forking. A launcher that exits before its descendants can
therefore leave unowned work behind or allow a timeout path to report completion
before containment is complete.

## Current state

Delegation and provider backends already centralize executable identity,
timeouts, bounded input and output, and descendant cleanup. Their prior
containment contract depended on post-creation Windows assignment and POSIX
process-group signaling. Those mechanisms cover common trees but leave a
startup window on Windows and do not establish ownership of session-escaping
Linux descendants.

## Approach

Move process ownership into a small core runner independent of routing and
delegation policy. On Windows, create the process with a kill-on-close Job
Object in its extended process-thread attribute list, start it suspended, retain
the exact primary-thread handle returned by `CreateProcessW`, and accept
`ResumeThread` only when the previous suspend count is exactly one. On Linux,
make the launcher a child subreaper, retain a pre-opened kernel children
descriptor, use pidfds when available, apply parent-death signaling before
`exec`, and drain every adopted generation after the direct child exits. Make
the supervisor non-dumpable before forking. Before target `exec`, create a
separate target session and install a `no_new_privs` seccomp policy that blocks
signals and queued signals addressed to the supervisor PID, its negative
process-group ID, or broadcast, plus supervisor-targeted `pidfd_open`,
`prlimit64`, scheduler and affinity mutations, `setpriority`, and `ioprio_set`,
while retaining ordinary target-to-child process management. Require a private
child-policy acknowledgement before external `READY`. Keep the target blocked
behind a separate exact `GO\n` plus EOF gate until the parent has durably stored
containment ownership and every I/O worker reference; cancellation closes that
gate without executing target code.

Keep standard input, output, status, descriptor-size, time, and cleanup bounds
explicit. Require a final `COMPLETE` receipt only after all descendants are
drained and the pinned children descriptor closes; EOF after `READY` or any
malformed, duplicate, or out-of-order terminal receipt is a containment error.
Bind every executable and wrapper artifact to one exact, ordered argv position
and reject unrelated, missing, duplicate, or reordered ephemeral and persistent
identity receipts during construction, freeze, and pre-launch revalidation.
Any unavailable ownership primitive or remaining descendant is a contained,
visible failure rather than a weak fallback.

Reuse the runner from provider, delegation, and release-tool subprocess
boundaries. Retain compatibility seams only for tests that explicitly replace a
legacy boundary; production calls always use the core implementation.

## Dependencies

None. The gap was discovered while giving the canonical release builder a
trusted Git subprocess boundary under AR-107.

## Acceptance

- [x] Windows assigns a kill-on-close Job Object atomically at process creation before child code can run.
- [x] Windows resumes the exact returned primary-thread handle only when its prior suspend count is one.
- [x] Linux owns and drains direct children, new-session descendants, and double-forked descendants.
- [x] Linux blocks target attempts to destroy or acquire a pidfd for its supervisor while preserving normal own-child signaling.
- [x] Linux blocks supervisor-targeted limit, scheduler, affinity, priority, and I/O-priority mutations while preserving the same operations for the target's own children.
- [x] The target cannot execute before an exact one-way GO handoff after containment state and I/O workers are durably owned.
- [x] Parent death terminates or adopts and drains every owned descendant without killing unrelated siblings.
- [x] A missing or malformed terminal supervisor receipt fails containment regardless of target return code.
- [x] Ephemeral and persistent launch receipts cover every artifact at one exact ordered argv position.
- [x] Provider, delegation, and release Git subprocesses share the policy-free core runner.
- [x] Input, output, status, descriptor-size, timeout, and cleanup budgets remain finite and non-blocking.
- [x] Unsupported ownership primitives fail visibly without a production weak fallback.
- [x] Native Windows and WSL Linux fault and escape regressions pass.
- [x] Warning-strict tests, line and branch coverage, Ruff, documentation, and security analysis pass.
