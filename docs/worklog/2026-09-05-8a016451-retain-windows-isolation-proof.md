---
title: "Retain Windows proof for implemented subprocess isolation"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, security, subprocess, windows]
related:
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 8a01645198308ee2b10cb342c95aabbb97aa1540
short: 8a016451
date: 2026-09-05
pr: null
related_issues:
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
---

# Worklog: retain the owner-held Windows proof

## Purpose

The sixth oldest-first disposition reaches a legacy record whose environment
isolation code exists but whose acceptance explicitly includes Windows.

## Approach

Trace installer and delegation callers to the shared least-privilege builder.
Run only the non-Windows environment/discovery/namespace package and record the
remaining owner-held native Windows/installed evidence. Keep every acceptance
item unchanged and make no duplicate tracker. Record AR-127's merged retirement
and closure read-back: 40 actual open trackers plus 99 legacy unfinished records.

## Challenges encountered

Windows execution is explicitly reserved for the owner's machine. POSIX tests
and shared source are not substituted for it; the record remains open.

## Decisions and alternatives

No new policy. Preserve ADR-0091's allowlist and safe PATH boundary. ADR-0105
means the historical full-release wording does not require an exhaustive run;
it does not waive the real platform proof or authorize native Windows work.

## Verification

64 tests passed, 12 Windows-named cases deselected, in 0.43s across subprocess
environment security, executable discovery and executable namespace. Sentinels
are synthetic; no real credential values were read or printed. Metadata/strict
docs pass for 1122 documents before this detail; policy/worklog/strict tracker/
diff checks pass. Runtime/test/script/workflow diff against 66282312 is empty.
No new install, live host draw, hosted dispatch or Windows run.

## Follow-ups

Merge the disposition, leave AR-129's Windows evidence with the owner, then
inspect AR-130. Isolated acceptance is still required before a future done flip.
