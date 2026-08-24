---
title: "Pass OpenClaw reset acknowledgements through both gates"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, telegram, reset, delivery, security]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
supersedes: []
superseded_by: null
type: worklog
commit: 3e71247a660ade4322af52b1446dc6fe99581db9
short: 3e71247a
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Pass OpenClaw reset acknowledgements through both gates

## Purpose

Complete native `/new` and `/reset` acknowledgement delivery through
OpenClaw's actual two-stage outbound path without weakening Agency's final-only
delivery boundary.

## Approach

The earlier reply-payload gate now waits for and verifies the same exact,
short-lived reset authorization created by `before_reset`, but does not consume
it. The later message-sending gate remains the one-use consumer. Session-bound
matching remains preferred; the already-bounded sessionless path still requires
exactly one matching authorization.

## Challenges encountered

Installing the first sessionless-correlation repair proved it was necessary but
insufficient. A changed `/new` reset native state yet delivered no acknowledgement
and created no Agency run. Installed-flow inspection showed that the native
reply reaches `reply_payload_sending` before the already-repaired
`message_sending` callback.

## Decisions and alternatives

The repair does not bypass either hook, send directly, alter OpenClaw source or
configuration, or change native/Agency inference. Authorization remains fixed
text, expiring, ambiguity-rejecting, and one-use at final dispatch. Replays and
two concurrent sessionless candidates fail closed.

## Verification

- The complete two-gate regression failed before implementation at exit 30.
- OpenClaw security, adapter, streaming, and installer slice: 246 passed,
  1 intentional skip.
- Focused Ruff check and format check passed.
- Documentation metadata, generated-policy, worklog, verification, and diff
  checks passed before installation.

## Follow-ups

Install Agency only into natively stopped OpenClaw and prove a changed fresh
`/new` acknowledgement plus Store-backed status delivery before touching
Hermes. Rule 4 native-child delivery remains unproven.
