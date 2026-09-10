---
title: "Preserve Codex keep-going recruitment context"
status: active
category: worklog
created: 2026-09-10
updated: 2026-09-10
tags: [codex, recruitment, reliability]
related:
  - docs/roadmap/issue-AR-431-preserve-keep-going-task-context.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
supersedes: []
superseded_by: null
type: worklog
commit: 05653bc9ed4222ddf4c779a105bd01fd79255fa4
short: 05653bc9
date: 2026-09-10
pr: null
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
