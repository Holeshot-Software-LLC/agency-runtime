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
commit: 24ddd4a0cca3859fdcefa8db34489843e93fb904
short: 24ddd4a0
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/830
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

## Native diagnostic result

Fresh OpenClaw session `agent:openclaw:ar404-20260909-priority-review-followup`
passed review trace `1b4de6af` in 82.956s and follow-up trace `97af70ee` in
58.928s, each with five Store-matching headers and authoritative response hashes.
Exact recorded hashes are `7d6aeb6fb4bcfa8c3714246242d6a1a2f6d575ae319f06362722ee3b72d89028`
and `45ef9fd59367f5fbac671bca162396914acf1cf200ccd33274f7759307db02b5`.
The original veto did not recur. No product repair is inferred from this sample.

The observer captured the review's accepted proposal/critic response. Its narrow
follow-up filter required literal average in the plan and therefore missed that
packet. This limitation is retained, not described as full critic capture. No
llm_input observer ran, so Store loads do not establish fresh full native card
injection. These are header/terminal diagnostic passes, not full-host certification.
Owner configuration restored byte-for-byte, observer errors zero, gateway RPC
healthy. Next active host is Hermes; AR-428 has an exact retained planning defect.
