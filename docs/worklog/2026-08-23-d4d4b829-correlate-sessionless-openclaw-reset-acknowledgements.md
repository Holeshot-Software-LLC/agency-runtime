---
title: "Correlate sessionless OpenClaw reset acknowledgements"
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
commit: d4d4b8294346df8d063703bd27d27e394fa81d24
short: d4d4b829
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Correlate sessionless OpenClaw reset acknowledgements

## Purpose

Restore the native `/new` and `/reset` acknowledgement when OpenClaw invokes
its supported outbound hook without the optional session context, while keeping
Agency's fail-closed outbound boundary intact.

## Approach

The existing reset hook still authorizes only OpenClaw's two fixed native
acknowledgement strings for a short lifetime. The generated bridge now records
the expected text with the hashed-session authorization. When outbound session
context exists, the original exact session-bound path is unchanged. When it is
absent, the bridge consumes an authorization only if exactly one active entry
matches the exact expected text.

## Challenges encountered

The native reset succeeded and created a fresh session, but no acknowledgement
was queued and no Agency run followed. Installed OpenClaw types and delivery
code confirmed that `message_sending` may omit `sessionKey` for this native
control response. The prior Agency gate treated that supported shape as
unauthorized and canceled it after the bounded wait.

## Decisions and alternatives

The repair does not infer a session, accept arbitrary text, bypass finalization,
send directly, alter OpenClaw source/configuration, or change model routing.
Zero candidates, multiple candidates, replay, wrong text, missing reset, and
expiry all remain rejected.

## Verification

- The live-shaped regression failed before implementation and passed afterward.
- OpenClaw security, adapter, streaming, and installer slice: 245 passed,
  1 intentional skip.
- Focused Ruff check and format check passed.
- Documentation metadata, generated-policy, worklog, verification, and diff
  checks passed before installation.

## Follow-ups

Install Agency only into natively stopped OpenClaw, restart it natively, and
prove a fresh `/new` acknowledgement plus changed Store-backed delivery before
touching Hermes. Rule 4 native-child delivery remains unproven.
