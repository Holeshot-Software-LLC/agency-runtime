---
title: "Prime bounded stdin before resuming Windows children"
status: accepted
category: decisions
created: 2026-07-13
updated: 2026-07-13
tags: [delegation, windows, subprocess, portability, reliability]
related:
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0043
type: decision
deciders: [maintainers]
---

# ADR-0043: Prime bounded stdin before resuming Windows children

## Context

Windows delegation children start suspended so the runtime can assign them to
a kill-on-close Job Object before user code executes. Command backends pass
fixed task input through an inherited pipe and use background workers to avoid
the classic full-pipe deadlock. Merely starting the stdin worker first does not
prove that the scheduler ran it before the child was resumed.

Hosted PowerShell companion tests showed the consequence: Console.In could
wait indefinitely when the child started before a small task payload and its
EOF were ready. Waiting for every payload while the reader remains suspended
is also unsafe because a payload larger than the pipe capacity can block the
writer forever.

## Decision

Close an empty input pipe synchronously before resume. For a non-empty payload
whose encoded size is at most 4096 bytes, start the writer and require its
completion event within five seconds while the child is suspended. Failure to
prime that bounded payload fails closed and terminates the owned process.

For larger payloads, start the writer first but do not wait while the child is
suspended; establish the Job Object and resume so the reader can drain the pipe.
Start stdout and stderr drainers before resume in both cases. Preserve exact
UTF-8/LF input and retain the original PowerShell Console.In regression.

## Consequences

- Common small tasks and explicit EOF are present before suspended Windows
  children inspect inherited input.
- Large tasks cannot deadlock against a suspended reader.
- Failure to schedule or close a small stdin payload becomes a bounded,
  explicit delegation error rather than a later backend timeout.
- Windows may spend up to five seconds failing closed during exceptional
  thread or pipe failure; successful completion normally signals immediately.
- POSIX process behavior remains asynchronous and unchanged.

## Alternatives

- **Rely on thread start order.** Rejected because start schedules work but
  does not establish completion before child resume.
- **Write every payload synchronously before resume.** Rejected because a full
  pipe deadlocks while its reader is suspended.
- **Resume before preparing any I/O.** Rejected because the child can observe
  an unprepared stdin boundary and fill undrained output pipes.
- **Use the null device for no input.** Rejected because PowerShell Console.In
  does not provide consistent EOF behavior for that device.
