---
title: "Preserve Codex keep-going recruitment context"
status: active
category: worklog
created: 2026-09-10
updated: 2026-09-10
tags: [codex, recruitment, reliability]
related:
  - docs/roadmap/acceptance/issue-AR-431.md
  - docs/roadmap/issue-AR-431-preserve-keep-going-task-context.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
supersedes: []
superseded_by: null
type: worklog
commit: 05653bc9ed4222ddf4c779a105bd01fd79255fa4
short: 05653bc9
date: 2026-09-10
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/840
related_issues:
  - docs/roadmap/issue-AR-431-preserve-keep-going-task-context.md
---

# Preserve Codex keep-going recruitment context

## Purpose

Resolve the observed parent recruitment failure within its proven scope.

## Approach

A read-only SQLite TEMP view restricts retained runs to sequences before1700;
it changes no durable receipt. Store reconstruction selects completed predecessor
01a0878e-6383-7201-848a-eca3280b283b and exactly reproduces the failed turn's
state revision5a66f8e5f238fdabb46e16a7f58378733d0fbb8a2ac224aba48668f42665ef82.
The same state yields new_intent for keep going and continuation for go ahead.
Add the missing exact phrase to existing state-aware classification and advance
classifier7/recipe22 while preserving historical read compatibility.

## Challenges encountered

The first diagnostic used to_dict instead of as_dict and stopped without writes;
the corrected read-only collection succeeds. The recruiter had a repaired shape
failure before the independent critic veto. Raw model packets were not retained,
so context loss is proven but a sole cause for the veto is not. The parent MCP
connection still returns Transport closed; staffing success cannot prove transport
recovery. Current process projection is stale independently of installed files.

## Decisions and alternatives

No manual specialist selection, critic relaxation, prior-assignment replay or
failed-receipt acceptance. Existing ADR-0064/0163 govern this narrow fix. Broader
semantic recruitment and Zcode work remain separately scoped.

## Verification

Old classifier negative control3 failed/27 passed; focused163 passed after repair.
Fresh native and required fast verification are pending. No exhaustive or Windows
workflow requested.

## Follow-ups

Build a canonical artifact after fast checks; inspect exact installed hook files
and trust, then demonstrate the contextual follow-up in a fresh native process.

## Installed candidate checkpoint

PR840 carries source05653bc9, canonical artifactf95e0ab6 and recipe22/classifier7.
Focused163, production1151/3skip, UI224, routing, Ruff788, docs, strict tracker and
frozen conformance188/188 passed. Build, strict Twine, artifact and installed
smoke pass; all616 package files match wheele1b6e5d47b31603b06e9f0f71f87df3692aaa7e9ecab8b0d673652e0e1e0ece7.
Before refresh, all651 projection37c1bf7d5eb0 files matched and a fresh app-server
reported8/8 trusted hooks. Candidate08689b5b8769 also has651 matching files, but
its8 changed hooks report modified/0trusted. This is a new trust requirement
caused by the necessary refresh, not a contradiction of the earlier8/8 result.
No native provider call or trust bypass was attempted. The package waits for
operator review in a fresh Codex TUI /hooks; then run the bounded completed-task
and keep-going follow-up. The stale parent and its separate closed MCP transport
are not repaired by installation. No isolated acceptance pass has run for AR-431.

## Merge record

PR840 merged at786f4611a094ef827fb0d8ed8bcfeccadbf3c93b with exact subject
`fix(routing): merge PR840 keep-going recruitment context repair`. The source
worktree is now historical. AR-431/#839 remains open and waiting_for_operator
for eight modified candidate hooks; native and isolated acceptance remain pending.
The next package uses a fresh owned worktree after normal native trust review.

## Trusted native initial review

Owner confirmed Codex trust on2026-09-10. Fresh hooks/list proves8/8 trusted
against the exact candidate hashes. Native session01a08b18-19fc-76f3-b5ea-4033b22c3291
initial trace01a08b18-1a43-7cb2-8b48-3d7f75b55d25 completed in78.818s with
recipe22/classifier7, four complete native cards, five matching Store headers
and authoritative finalization. The collector compares native developer context
and exact native user/final bytes with immutable Store evidence; no prior
assignment replay, trust bypass, specialist delegation or execution claim.
The exact same-session keep-going follow-up remains next, then isolated review.

## Native follow-up and acceptance packet

Native session01a08b18-19fc-76f3-b5ea-4033b22c3291 passed the frozen initial
review in78.818s and exact keep-going follow-up in157.872s. Follow-up trace
01a08b1a-f50d-76d0-bb24-eb624109f97f is classifier7 continuation of completed
01a08b18-1a43-7cb2-8b48-3d7f75b55d25. Recipe22 applies bounded context and fresh
inference, with no cache/assignment replay. Four initial and five follow-up full
cards, all five Store headers and authoritative response hashes40bace52/5c36ceba
match exact native bytes. The follow-up retained an invalid reranker reply and
a primary recruiter timeout; configured content fallback succeeded, then the
independent critic accepted staffing. No caller retry, manual selection, bypass,
delegation or executed-test claim. PR842 carries these observations; isolated
acceptance remains pending. No all-host reliability or historical-receipt repair.

Native evidence PR: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/842
Additional focused critic-boundary5 tests passed in0.37s. The original fast
spine/conformance remain applicable to unchanged source05653bc9/artifactf95e0ab6.

Local packet validation caught four out-of-range excerpt ends; corrected before
any isolated verifier call. No review pass was consumed by this local check.
