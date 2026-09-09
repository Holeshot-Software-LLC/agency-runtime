---
title: "Preserve completed-task subject context and repair Claude installation"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, native, context]
related:
  - docs/roadmap/issue-AR-421-preserve-completed-task-followup-context.md
  - docs/roadmap/issue-AR-422-preserve-claude-update-permissions.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-421-preserve-completed-task-followup-context.md
  - docs/roadmap/issue-AR-422-preserve-claude-update-permissions.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Preserve completed-task subject context and repair Claude installation

## Purpose

The fixed native sample reproduces an ordinary short follow-up staffing failure.
The preceding review completes, but "go for it" loses its bounded subject before
staffing. Separately, repeated Claude npm updates undo temporary permission fixes.

## Approach

Classifier6 preserves correlation for completed-task contextual replies and
revisions, always requiring fresh selection and execution decisions. Completed
workers are never replayed. Existing transcript-free context, source-state guard,
independent critic and validators remain unchanged; old classifier versions stay
readable. New explicit tasks, failed terminal states and untrusted context do not
inherit completed-task correlation.

Claude's own updater receipt matches its latest namespace replacement. An inert
offline npm fixture reproduces775parents under process002/additional npm mask0.
Mask022 does not repair every path, so no npm user config was changed. The native
installer under077 provides its supported versioned binary and PATH launcher.
Normal trust and Agency refresh pass; active user terminals remain untouched.

## Challenges encountered

One initial regression command accidentally imported candidate source through
pytest's root configuration. It is not original-source evidence. The corrected
negative control imports and asserts original classifier5 before pytest starts;
seven positive regression cases fail and12negative cases pass. Ruff's complexity
limit required extracting the terminal contextual-reply decision without changing
active-turn behavior. Original-source integration fails with missing context.

## Decisions and alternatives

ADR-0064/0163 govern bounded correlation and fresh inference. ADR-0055 governs
executable identity: use the host's native installer, never copy or weaken trust.
A complete response without accepted staffing remains a failed suite result.

## Verification

Focused152pass; original-source negative control7fail/12pass. Named production
spine1151pass/3skip in117.94s; UI224pass; Ruff check/format pass. Native Codex
baseline review73.147s/multi-step114.055s have exact accepted terminal hashes;
short follow-up84.122s fails staffing. Native injection inspection and remaining
hosts are pending. No exhaustive or Windows dispatch.

## Follow-ups

Install a verified candidate artifact, repeat the same fixed requests and obtain
isolated acceptance forAR-421/422. Complete Hermes default adoption, OpenClaw
injection and Zcode answering gates underAR-404. Preserve every baseline outcome.
