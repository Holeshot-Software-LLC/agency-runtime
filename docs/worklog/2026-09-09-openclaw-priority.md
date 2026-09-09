---
title: "OpenClaw-first reliability continuation"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [openclaw, reliability, staffing]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# OpenClaw-first reliability continuation

## Purpose

The owner prioritizes OpenClaw, Hermes, Codex, Claude and defers Zcode. This
supersedes the immediate AR-423 work order after a read-only bootstrap.

## Approach

New owned tree starts at synchronized `e9538ed8`. Inspect the retained failed
OpenClaw follow-up before selecting a repair. Trace `bdf2e524` has successful
planner/recruiter stages, a wrong-neighbor critic veto, no saved routing proposal
and no authoritative finalization. One bounded fresh review/follow-up sequence
will capture the actual critic packet through a byte-preserving local observer.

## Challenges encountered

The old receipt's qualified reason does not retain the selected team, so it
cannot establish that the critic veto was erroneous. Capture only the synthetic
average-function request and its follow-up; do not record credentials or headers.

## Decisions and alternatives

Preserve inference, critic, validators, trust and native limits. The observer
changes observability only, restores owner config in finally, and has no retry
loop. Do not reopen the original failed receipt or substitute selected workers.

## Verification

Read-only inspection confirms main clean and synchronized, recipe 19 merged,
and the original failed receipt unchanged. Observer smoke precedes native work.

## Follow-ups

AR-404 retains the five-host umbrella. Work proceeds OpenClaw, Hermes, Codex,
Claude; Zcode remains documented and deferred. AR-423 isolated closure is queued.

Observer smoke passed request/response byte preservation, credential forwarding
without capture, exact synthetic review/follow-up filtering and unrelated request
exclusion. The script and smoke result are retained under AR-404 evidence.
