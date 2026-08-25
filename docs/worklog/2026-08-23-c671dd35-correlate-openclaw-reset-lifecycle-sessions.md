---
title: "Correlate OpenClaw reset lifecycle sessions"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, telegram, reset, delivery, security]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
supersedes: []
superseded_by: null
type: worklog
commit: c671dd35159adebb4899447a59e8aa52c6c24191
short: c671dd35
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Correlate OpenClaw reset lifecycle sessions

## Purpose

Deliver OpenClaw's exact native `/new` and `/reset` acknowledgement when its
reset lifecycle supplies different session identities to the reply, reset,
and final-message callbacks.

## Approach

Exact session correlation remains the first choice. If that lookup misses,
the bridge applies the existing bounded fallback regardless of whether the
callback supplied a session: exactly one recent authorization must match the
fixed native acknowledgement text. The reply-payload gate verifies without
consuming it; the final message gate remains the one-use consumer.

## Challenges encountered

The installed content-free trace proved that reply-payload observation ran 2
ms before reset authorization. Both callbacks supplied sessions, but their
lifecycle identities differed. The prior code treated any supplied session as
authoritative, so it never considered the one valid authorization and canceled
after the bounded wait. No acknowledgement, Agency run, or routing decision
followed.

## Decisions and alternatives

The repair does not infer or log an identity, bypass a gate, send directly,
alter OpenClaw source/configuration, or change inference. Exact matches still
win when multiple resets coexist. A mismatched session with zero or multiple
candidates fails closed, as do replay, wrong text, and expiry.

## Verification

- Distinct pre-reset/post-reset/delivery-session regression failed before
  implementation at exit 30 and passed afterward.
- The regression also proves a mismatched supplied session cannot select two
  concurrent authorizations.
- OpenClaw security, adapter, streaming, and installer slice under umask
  `0077`: 246 passed, 1 intentional skip.
- Full Ruff check and format check passed.
- Documentation metadata, generated-policy, worklog, verification, and diff
  checks passed before installation.

## Follow-ups

Install Agency only into natively stopped OpenClaw and prove one changed
`/new`, then continue Store-backed status/skill delivery. Rule 4 native-child
delivery remains unproven.
