---
title: "Use an authoritative bounded provider chain with allowlisted CLI transports"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-13
tags: [providers, routing, authentication, subprocess, security]
related:
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-06-cli-authenticated-judge-providers.md
  - docs/roadmap/issue-AR-21-fully-resume-windows-children.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0008-ordered-provider-fallback.md
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0035
type: decision
deciders: []
---

# ADR-0035: Use an authoritative bounded provider chain with allowlisted CLI transports

## Context

Agency Runtime supports ordered judge fallback, but the interactive setup path
previously represented only one legacy judge. A user could remove an endpoint
from the typed provider list and still have legacy judge or Ollama settings
invoke it invisibly. Configuration also described a CLI provider without a
real transport contract.

CLI-authenticated hosts can reduce duplicate credential setup, but invoking a
general agent CLI introduces process, tool, configuration, output, timeout,
and Windows command-shim risks. HTTP validation and model discovery introduce
their own credential-redirect and untrusted-output boundaries.

## Decision

Use one ordered typed provider chain with at most four entries, matching the
runtime attempt budget. When the chain is nonempty it is authoritative: after
its final failure, selection goes directly to deterministic token routing.
Legacy judge and separate Ollama settings apply only when no typed chain exists.

Allow CLI-backed judge entries only for explicitly supported Codex and Claude
transports. Require a stable noninteractive structured-output contract and
separate executable discovery, authenticated-session status, and usable
capability. Deliver prompts over standard input, run in an empty temporary
working directory, isolate general home and temp roots while retaining only the
host authentication root, disable tools and project customizations, bound both
output streams while draining them concurrently, enforce a finite timeout, and
kill the owned process tree on timeout. Cap tasks at 16 KiB and recursively
redact them from commands, output, structured metadata, and errors. Use a
kill-on-close Job Object with suspended assignment on Windows and an owned
process group on POSIX. A parent that exits while descendants remain is cleaned
up and treated as a failed delegation.

Resolve Windows process entry points without passing user-controlled arguments
through `.cmd` or `.bat`. Prefer a sibling native executable, use a sibling
PowerShell entry point with discrete arguments, or fail closed. Validate model
identifiers before argv construction.

Use the same provider-validation service in the wizard and doctor. Credentialed
remote HTTP calls require HTTPS; literal loopback HTTP is the only exception.
Provider URLs reject user information, query strings, and fragments, and
credentialed calls do not follow redirects. Remote catalogs are byte-, count-,
string-, and terminal-control bounded. Direct keys use hidden input and
owner-private atomic configuration writes; environment-key references remain
supported.

## Consequences

- Provider order shown to the user is the exact order the selector attempts.
- Removing an entry cannot leave a hidden billed or network fallback.
- Existing CLI sessions can supply judge decisions without copying their
  credentials into Agency Runtime configuration.
- Unsupported or older CLI versions fail to deterministic routing rather than
  receiving a best-effort invocation.
- Four entries are a deliberate bounded latency and resource limit; larger
  chains require a new decision and attempt-budget design.
- Shared process and HTTP boundaries also harden delegation, detection, and
  diagnostics.
- A backend cannot leave a detached child behind after returning success; that
  ownership violation becomes an explicit failure after bounded cleanup.

## Alternatives

- Append legacy providers after every typed chain. Rejected because it violates
  user-visible ordering and can make an unexpected network request.
- Accept arbitrary CLI command templates. Rejected because shell-neutral input
  does not make an unknown agent contract safe or parseable.
- Pass prompts as command arguments. Rejected because prompts are private,
  length-variable, and unsafe around Windows batch shims.
- Capture unlimited output in temporary files. Rejected because a child can
  exhaust disk or memory before post-process truncation.
- Follow same-origin HTTP redirects. Rejected in favor of a simpler fail-closed
  credential boundary across every provider path.

## Provenance

AR-05 and AR-06 record configuration, runtime, and verification evidence. The
implementation commit is linked through the roadmap and worklog after final
validation.
