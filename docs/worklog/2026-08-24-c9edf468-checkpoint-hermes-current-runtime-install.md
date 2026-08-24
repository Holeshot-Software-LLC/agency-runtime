---
title: "Worklog detail: Checkpoint Hermes current runtime install"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [hermes, litellm, installer, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
supersedes: []
superseded_by: null
type: worklog
commit: c9edf468aa9072e34b6c52910597ad560a5ce631
short: c9edf468
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
---

# Worklog detail: Checkpoint Hermes current runtime install

## Purpose

Record the bounded Hermes Agency-only install and native restart from the same
checkout before beginning fresh live Telegram evaluation.

## Approach

The operator resolved the effective Hermes home and owning systemd user unit,
verified that no user turn was active, backed up the WAL-consistent Agency
Store, and retained hashes rather than secret-bearing native configuration.
The owning service was stopped, Agency alone was installed with the dashboard
disabled, and the same service was restarted natively. Hermes itself was not
reinstalled and none of its native model routes were changed.

## Challenges encountered

The native CLI has no `status --json` surface; that unsupported invocation is
retained as a failed attempt and was not repeated. The service stop left a
systemd failed/exit-code receipt even though the gateway exited and was proven
down. A prior broad native status view emitted masked credential prefixes and
a transport identifier, so it was excluded from durable artifacts and all
subsequent checks used field-filtered outputs.

## Decisions and alternatives

The install checkpoint makes no activation, inference-attribution, actual
answering model, delegation, native-child, Rule 4, or matrix-cell claim. The
existing Hermes `task-general` route and five fallbacks remain native host
configuration; only the Agency harness profile requests the opaque
`task-agency-router` LiteLLM alias.

## Verification

- Pre/post native config, native environment, plugin inventory, and Agency
  config hashes are unchanged.
- Store source and online backup integrity are `ok`, schema is 47, and the
  contractor count remains 15.
- Agency install `0a3d141a...` completed without dashboard or host restart;
  its launcher resolves to this checkout and runtime digest `573a6a14...`.
- The same owning service is active/running with result `success` and zero
  restarts; plugin doctor reports eight hooks and zero tools.
- Documentation metadata, policy availability, worklog, verification, and
  diff checks passed.

## Follow-ups

Run one fresh Hermes reset/status/skill/substantive sequence and correlate
native transcript, Store rows, Agency inference receipts, and Telegram delivery
without changing native routes or retrying a failed input unchanged.
