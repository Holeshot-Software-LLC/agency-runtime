---
title: "AR-21: Make Windows child startup deterministic and fail closed"
status: in_progress
category: roadmap
created: 2026-07-13
updated: 2026-07-13
tags: [windows, subprocess, delegation, reliability, security]
related:
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0043-prime-stdin-before-windows-child-resume.md
  - docs/decisions/0044-preclose-bounded-windows-child-stdin.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-21
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/22"
depends_on: []
blocks: [AR-17]
---

# AR-21: Make Windows child startup deterministic and fail closed

## Problem

Windows delegation children start suspended so the runtime can assign them to
a kill-on-close Job Object before user code executes. The native resume helper
treated every non-error ResumeThread call as a fully runnable thread even
though a return above one leaves it suspended.

Hosted Windows PowerShell companion runs still reached the backend timeout
after the prior completion-event priming change. That proved scheduling a
writer against a newly created pipe was not a durable EOF boundary on every
supported runner. Separately, a suspend count above one belongs in part to
another actor; consuming it could cross a debugger or endpoint-security
boundary.

## Current state

CPython's Windows launch path correctly inherits only duplicated child-side
standard handles, and Job Object assignment does not duplicate pipe handles.
Local native PowerShell tests passed, but hosted Python 3.10 and 3.14 timed out
all five companion variants at Console.In.ReadToEnd. The startup contract needs
immutable input state before process creation plus strict ownership of the one
CREATE_SUSPENDED count.

## Approach

For empty or bounded input up to 4096 encoded bytes, fill an anonymous pipe and
close its writer before creating the Windows child. Pass only the read end to
the child and close the parent's copy immediately after creation, giving
PowerShell deterministic data and EOF without a scheduler race or disk spill.
Keep larger input on the asynchronous writer so a suspended reader cannot fill
the pipe and deadlock.

Require the complete thread snapshot to contain exactly one process-owned
primary thread, reopen it with owner verification, and resume it exactly once.
An incomplete snapshot, extra thread, recycled ID, zero or greater-than-one
suspend count, native failure, or missing handle fails closed and triggers
existing tree cleanup. Never drain suspension counts that may belong to another
actor. Retain a child-startup marker in the hosted integration so future
failures distinguish launch from stdin delivery.

## Dependencies

This bug was surfaced by AR-17's hosted Windows matrix and blocks that release
gate. It hardens ADR-0035's suspended Job Object containment through ADR-0044,
which supersedes ADR-0043's scheduling-dependent priming mechanism.

## Acceptance

- [x] Empty and at-most-4096-byte input is complete and at EOF before process creation.
- [x] At-least-4097-byte input remains asynchronous and cannot block a suspended reader.
- [x] Exact UTF-8 data is preserved across both pipe paths.
- [x] Only the runtime-owned suspend count of one is released.
- [x] Already-running, externally suspended, missing-handle, and native-error states fail closed.
- [x] Job Object assignment still precedes child execution.
- [x] Hosted diagnostics distinguish child startup from stdin EOF failure.
- [ ] The original Windows PowerShell integration passes on hosted Python 3.10 and 3.14.
- [ ] Exact coverage, review, merge, and tracker closure pass.
