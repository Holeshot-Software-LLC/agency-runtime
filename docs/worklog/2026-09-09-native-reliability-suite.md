---
title: "Freeze ordinary native reliability requests and preserve follow-up failure"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, native, staffing]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: c13f3b72730d1790280e4696b7974742dd2eb722
short: c13f3b72
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Freeze ordinary native reliability requests and preserve follow-up failure

## Purpose

The owner requested demonstrated reliability after repeated valid staffing
failures. Freeze a bounded15turn native sample before provider calls and retain
all outcomes. This is acceptance sampling, not a statistical reliability claim.

## Approach

Three unchanged requests on each of five hosts cover an ordinary review, a short
same-session follow-up and a multi-step correction. One outer attempt per case
per phase, unchanged internal budgets,360second process deadline. Record exact
staffing, headers, native card injection, finalization hash and terminal state;
missing host gates are blocked. Baseline source77f6773f is clean and synchronized.

## Challenges encountered

Current parent staffing failed again. Its exact receipt and state reconstruction
show available prior context discarded by executable-new-intent classification
for "go for it". Reconstructed state revision agrees with persisted metadata;
this does not reconstruct the unavailable recruiter proposal or adjudicate the
critic veto. Reranker passes; cold embedding takes39.653seconds. Claude trust
still fails after external package replacement; earlier native success is historical.

## Decisions and alternatives

Preserve inference-only staffing, independent critic and all validators. Keep
all failed attempts and blocked gates; a later pass never replaces a failure.
Do not change answering models or provider routes to improve apparent speed.

## Verification

Read-only repository, exact failed receipt and same-state classification checks
completed. Documentation and diff checks accompany the frozen checkpoint before
live calls. No production source changed in this checkpoint.

## Follow-ups

Execute the fixed baseline, repair reproduced causes and finish Hermes,
OpenClaw, Claude and Zcode gates underAR-404. Repeat the same requests after repair
and complete isolated acceptance before closing any issue.
