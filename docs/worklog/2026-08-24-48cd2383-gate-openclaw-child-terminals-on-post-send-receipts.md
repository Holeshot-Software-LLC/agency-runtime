---
title: "Worklog detail: Gate OpenClaw child terminals on post-send receipts"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, delivery, lifecycle, telegram]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0169-authorize-finalized-openclaw-child-announcements.md
supersedes: []
superseded_by: null
type: worklog
commit: 48cd2383856b101ff721d89a67507369ce9d9d2f
short: 48cd2383
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md
---

# Worklog detail: Gate OpenClaw child terminals on post-send receipts

## Purpose

Prevent Agency from calling a native OpenClaw child delivered before the host
has accepted its finalized announcement. The retained live draw reached
Telegram, but `cleanup: delete` removed OpenClaw's child registry entry before
the deferred end hook could close Agency's worker and delegation.

## Approach

Store schema 48 separates immutable child execution outcome from delivery
state. Child `agent_end` records `pending` without terminalizing. Only an exact
finalized parent response plus `message_sent(success=true)` atomically records
`delivered` and closes lifecycle; explicit send failure stays open.

The installed host exposes no send-attempt identifier shared across every
pre-send and post-send hook. The plugin therefore records every allowed text
send in a bounded ledger and admits only one active match across every supplied
target, channel, account, conversation, session, run, and canonical response
hash. Active attempts remain at least one hour, consumed ambiguity tombstones
remain 24 hours, and capacity exhaustion cancels rather than evicts evidence.

On gateway startup, only durable receipt-backed pending or failed rows become
`interrupted`. Their observed execution outcome remains available separately,
while worker and delegation lifecycle terminalize as failure. Unobserved work
is not swept, and generic end or stop APIs cannot bypass the delivery gate.

## Challenges encountered

The first draft treated pre-transport `message_sending` as delivery. Review
rejected that because OpenClaw emits it before platform acceptance. A second
draft matched post-send events only by optional session and response hash;
review demonstrated stale, delayed, and ordinary-identical callbacks could
manufacture delivery. Local inspection confirmed that the durable queue ID is
not exposed to either hook, Telegram may omit session/run identity, and Slack's
same-named message IDs refer to different inbound and outbound objects.

Review also found that startup interruption could project a successful worker
from an `ok` execution outcome despite missing delivery, and that the
outcome-free stop API bypassed the pending/failed gate. Focused regressions
were added before each repair. An initial broad test run inherited shell umask
`0002` and correctly failed the trusted configuration-parent boundary; the
unchanged run under owner-private `0077` passed.

## Decisions and alternatives

The implementation does not change OpenClaw source or model configuration,
infer delivery from child execution, rely on a duplicate cleanup hook, persist
raw provider/transport errors, or treat an alias as an actual model. A crash
after platform acceptance but before Store commit remains interrupted rather
than inventing success. This operational receipt remains distinct from
ADR-0156 Rule 4 proof.

Hermes remained the active break-glass host. Codex OAuth/configuration/canary,
Claude, ZCode, OpenClaw's native `task-general`, and Agency's separate
`task-agency-router` route were not changed or re-proven.

## Verification

- Focused OpenClaw/Store/installer/dispatch suite: 294 passed, 1 unrelated
  platform skip under `umask 077` and `/usr/bin/python3.12`.
- Named fast Python production spine: 852 passed, 3 skipped.
- Full Ruff check and format: 682 files.
- Docs metadata, policy availability, worklog, and verification: 785 files.
- Dashboard UI: 134 passed.
- `git diff --check` passed.
- Two independent review passes ended with no unresolved Critical, High, or
  Medium finding; final verdict was GO for the scoped checkpoint.
- Exhaustive workflow-dispatch corpus was not run, as required for this local
  package.

## Follow-ups

Back up the live Store before schema migration, install this Agency-only build
while OpenClaw is natively stopped, and prove one genuinely changed Telegram
child result closes the exact Store worker/delegation. Only after OpenClaw
passes, perform the equivalent Hermes package. Tracker creation, publication,
and ADR-0156 Rule 4 remain separately authorized or separately evidenced.
