---
title: "Own subprocess trees atomically across Windows and Linux"
status: accepted
category: decisions
created: 2026-07-19
updated: 2026-07-20
tags: [security, processes, delegation, windows, linux, portability]
related:
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
superseded_by: null
id: ADR-0073
type: decision
deciders: [maintainers]
---

# ADR-0073: Own subprocess trees atomically across Windows and Linux

## Context

The provider and delegation boundaries already require trusted executables,
argument-array execution, bounded streams, finite timeouts, and descendant
cleanup. The earlier implementation created a Windows child suspended and then
assigned its Job Object, leaving an ownership gap if the launcher died before
assignment. It separately used a POSIX process group, which a descendant can
leave with `setsid()` or a double fork. Process-group absence after the direct
child exits does not prove that all work Agency started has ended.

Release tooling needs the same containment properties without importing routing
policy, configuration hydration, YAML parsing, or the delegation graph.
Duplicating a second partial process runner would create inconsistent security
and timeout behavior.

## Decision

Use one policy-free owned-process core for every bounded subprocess boundary.
The core accepts an already prepared, identity-checked argument vector and
explicit input, output, status, descriptor-size, time, and cleanup budgets.
Provider and delegation layers adapt domain results around it; release tooling
imports the core directly. Retain ADR-0044's preclosed standard-input rule for
UTF-8 payloads at or below 4096 bytes; this decision replaces its
post-creation Job assignment and Toolhelp primary-thread lookup.

On Windows, construct a kill-on-close Job Object before process creation and
place it in `PROC_THREAD_ATTRIBUTE_JOB_LIST`. Create the child suspended so no
user code runs before ownership exists. Retain the exact primary-thread handle
returned by `CreateProcessW` and resume it only when `ResumeThread` reports a
previous suspend count of exactly one. Any unavailable primitive, unexpected
suspend count, creation failure, or surviving descendant fails closed and
closes the Job.

On Linux, run the immediate launcher as a child subreaper, install parent-death
signaling before `exec`, make the supervisor non-dumpable before it forks, retain
a pre-opened `/proc/self/task/<pid>/children` descriptor, and use pidfds for
identity-stable signaling. The target enters a separate session and inherits a
`no_new_privs` seccomp policy that denies signal and queue operations addressed
to the exact supervisor PID, its negative process-group ID, or the broadcast
target, and denies supervisor-targeted `pidfd_open`, `prlimit64`,
`sched_setparam`, `sched_setscheduler`, `sched_setaffinity`, `sched_setattr`,
`setpriority`, and `ioprio_set`. Ordinary target-to-child process and resource
management remains available. The policy is installed before `exec` and
acknowledged on a private, bounded child-policy pipe before the supervisor emits
external `READY`.

`READY` does not release target code. The gated child alone retains a separate
one-shot descriptor and requires exactly `GO\n` followed by EOF. The parent
stores the status channel, containment owner, mutable lifecycle state, and every
I/O worker reference before writing that receipt as its final one-way commit.
Cancellation writes the distinct exact `CANCEL\n` receipt and closes the gate,
so an interruption before commit cannot execute the target. An ambiguous
interruption after the write is treated as though execution began: the complete
owned tree is drained before the original interruption is re-raised.
Unsupported architectures, seccomp, pidfds, procfs, or policy setup fail before
readiness instead of weakening the contract.

After the direct child exits or a timeout occurs, repeatedly enumerate, signal,
reap, and re-enumerate adopted generations until the tree is empty or the
finite cleanup budget expires. Only after the tree is empty, the root result is
known, and the pinned children descriptor closes successfully may the
supervisor emit terminal `COMPLETE`. Consumers require exactly one `READY`,
defined bounded informational records, and exactly one final `COMPLETE`.
Truncated status, EOF after `READY`, explicit failure, duplicate or out-of-order
terminal records, and abnormal supervisor exit are containment failures
regardless of the target return code.

Prepared launch receipts bind every launch-critical artifact to exactly one
strictly increasing argv position. The first artifact covers `argv[0]`, the
launcher prefix ends after the last artifact, and ephemeral or persistent
identities must cover the same paths. Construction, freezing, and immediate
pre-launch revalidation reject missing, duplicate, reordered, or unrelated
artifact identities.

There is no production fallback to post-creation Windows assignment or
process-group-only Linux cleanup. Platforms without the required ownership
contract report an explicit unsupported or containment failure. Compatibility
adapters may preserve narrow monkeypatch seams for tests, but normal execution
always uses the core.

## Consequences

- A successful subprocess result means the owned process tree is empty, not
  merely that the direct child returned.
- Windows removes the pre-assignment ownership and parent-death gap.
- Linux contains session-escaping and double-forked descendants without
  signaling unrelated siblings.
- Linux targets can manage their own children normally, but cannot use inherited
  signal, pidfd, limit, scheduler, affinity, priority, I/O-priority, ptrace, or
  proc-memory interfaces to destroy, stall, or rewrite their supervisor.
- External readiness no longer creates an execution race: target code remains
  gated until containment and I/O ownership are durable.
- A missing terminal cleanup receipt can no longer turn supervisor loss into a
  successful subprocess result.
- Release, provider, and delegation paths share one audited containment
  implementation without coupling release tooling to routing policy.
- Strong ownership has a clear portability boundary; unsupported systems fail
  visibly instead of silently receiving weaker semantics.
- Kernel descriptors, handles, streams, and temporary resources require
  bounded cleanup on every success and failure path.
- Linux `no_new_privs` intentionally excludes launchers that require set-user-ID
  or file-capability elevation. The contract assumes an identity-approved
  executable and its descendants; it is not a sandbox against root,
  administrator, or a separately cooperating process already trusted under the
  same operating-system account.

## Alternatives

- **Keep post-creation Job assignment.** Rejected because launcher death before
  assignment can leave the suspended child outside the kill-on-close boundary.
- **Use only a POSIX process group.** Rejected because a descendant can create
  a new session or double-fork out of that group.
- **Search the global process table by parent PID.** Rejected because PID reuse,
  races, permissions, and unrelated processes make that an unsafe ownership
  claim.
- **Maintain separate runners in release and delegation code.** Rejected
  because drift would make equivalent subprocess boundaries enforce different
  security and resource contracts.
- **Best-effort cleanup on unsupported platforms.** Rejected because silent
  degradation would make success evidence stronger than the actual ownership
  guarantee.
