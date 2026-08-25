---
title: "Worklog detail: Deliver correlated OpenClaw native errors"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, errors, delivery, finalization, security]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0168-deliver-openclaw-native-errors-through-exact-terminal-evidence.md
supersedes: []
superseded_by: null
type: worklog
commit: 630fc148295763b18bc5f6ed81b1f86af3b34990
short: 630fc148
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Deliver correlated OpenClaw native errors

## Purpose

Surface an exact OpenClaw-owned native failure notice instead of canceling it
as a headerless Agency answer, while retaining terminal Store evidence and all
ordinary answer, header, safety, and child-delivery checks.

## Approach

The generated OpenClaw plugin now observes failed `agent_end` events and stores
only bounded SHA-256 session/run correlation keys for 30 seconds. One matching
final payload explicitly marked `isError` may ask the Python bridge to close the
exact Store turn `response_invalid` with `native_host_error`. Only an
authoritative exact receipt permits the existing one-use outbound seal. A later
successful end clears an earlier failure marker, and no raw native error or
message crosses the bridge or enters the Store.

The installer now requires the audited `agent_end` capability. Tests cover
wrong identity, absence, expiry, replay, fallback clearing, malformed receipts,
bridge failure, runtime-disable races, authoritative Store readback,
specialist expiry, and installer negotiation.

## Challenges encountered

The expected-red run proved two missing contracts: OpenClaw `agent_end` was not
registered and the bridge did not implement `native_error`. The first repair
run then exposed a missing `responseHash` field in bridge serialization before
exact correlation could pass. Repository policy checks initially could not
import the checkout module from the script entry point; rerunning with the
checkout explicitly on `PYTHONPATH` passed. Direct `ruff` and `python -m ruff`
were unavailable in the ambient interpreter, so the repository virtual
environment executable was used and passed.

## Decisions and alternatives

ADR-0168 owns the durable decision. The repair does not add an Agency header to
an error, send directly, change OpenClaw source/configuration/model routing, or
relax ordinary finalization. Delivering a native error remains failure evidence,
not Agency success or substantive acceptance.

## Verification

- Focused OpenClaw suites: 251 passed, 1 intentional skip.
- Full repository Ruff check: passed.
- Full repository Ruff format check: passed.
- Documentation metadata, policy availability, worklog, and verification checks: passed.
- `git diff --check`: passed.
- Independent security review: no blocking findings.

## Follow-ups

Install this Agency-only candidate into natively stopped OpenClaw, then prove a
fresh exact status turn and a genuinely changed bounded substantive Telegram
turn. Continue Hermes only after OpenClaw's host-scoped acceptance set passes.
