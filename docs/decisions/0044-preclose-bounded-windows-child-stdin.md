---
title: "Preclose bounded Windows child stdin and own one suspension"
status: superseded
category: decisions
created: 2026-07-13
updated: 2026-07-20
tags: [delegation, windows, subprocess, portability, reliability, security]
related:
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-21-fully-resume-windows-children.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0043-prime-stdin-before-windows-child-resume.md
superseded_by: docs/decisions/0073-own-subprocess-trees-atomically.md
id: ADR-0044
type: decision
deciders: [maintainers]
---

# ADR-0044: Preclose bounded Windows child stdin and own one suspension

## Context

Windows delegation children start suspended so Agency Runtime can assign them
to a kill-on-close Job Object before user code executes. ADR-0043 started a
background stdin writer and waited for a completion event before resume when
the payload fit in the pipe. Local tests passed, but hosted Windows Python 3.10
and 3.14 still timed out all PowerShell companion variants while reading stdin.
A scheduled writer and an observed close were therefore not a sufficiently
durable process-creation boundary.

ResumeThread returns the previous suspend count. CREATE_SUSPENDED contributes
one count to the primary thread. A value above one means the thread remains
suspended by another actor, while zero means it was already runnable. Repeated
resume calls could consume counts owned by a debugger or endpoint-security
product.

## Decision

For Windows input whose UTF-8 encoded size is at most 4096 bytes, create an
anonymous pipe, write the complete payload, and close the writer before child
creation. Give the child only the read descriptor and close the parent's read
descriptor immediately after creation. Empty input uses the same preclosed pipe.
Larger payloads retain the asynchronous writer so a suspended reader cannot
cause a full-pipe deadlock. No task bytes are placed in argv or durable files.

After Job Object assignment, require a complete snapshot containing exactly one
process-owned primary thread. Reopen that thread, verify the handle still
belongs to the child, and resume it exactly once. Accept only a previous count
of one. An incomplete snapshot, extra thread, recycled ID, zero or
greater-than-one count, native failure, or missing handle fails closed and
terminates the owned process tree. Agency Runtime never drains suspension
counts it did not create.

## Consequences

- Bounded input and EOF exist before PowerShell or another child can start.
- The common path needs no stdin worker, completion event, or scheduling wait.
- Large input remains non-blocking while the child is suspended.
- Unexpected debugger or endpoint-security suspension causes a visible,
  contained delegation failure instead of crossing an ownership boundary.
- Exact boundary tests cover empty, 4096-byte, 4097-byte, and multibyte input.
- ADR-0043 remains as the faithful record of the superseded completion-event
  design.

## Alternatives

- **Keep waiting for a background writer.** Rejected because hosted evidence
  showed that the scheduling-dependent contract was not portable.
- **Drain every suspend count to zero.** Rejected because counts above one may
  belong to another actor.
- **Synchronously write every payload before launch.** Rejected because an
  unbounded pipe write can block before the reader is runnable.
- **Store task input in a temporary file.** Rejected because task content would
  gain a durable filesystem lifetime and cleanup boundary.
