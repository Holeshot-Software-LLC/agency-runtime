---
title: "Worklog: Stabilize hosted Windows PowerShell gate"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [ci, windows, powershell, testing]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-23-hosted-windows-powershell-gate.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 11387ad6e57ffbfeffc443c67f60ef343b93fbe8
short: 11387ad
date: 2026-07-13
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18"
related_issues:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-23-hosted-windows-powershell-gate.md
---

# Worklog: Stabilize hosted Windows PowerShell gate

## Purpose

Remove a hosted-Windows false negative that blocked an otherwise green release
matrix after newly written PowerShell companion scripts exhausted the 20-second
integration-test allowance during cold startup.

## Approach

Compared the complete Python 3.10 and 3.14 failure summaries. The first two or
three companion parameters timed out, while later parameters on the same stdin,
Job Object, and resume paths passed. All exact-stdin boundary cases also passed.
Raised only the Windows PowerShell integration-test allowance to 60 seconds and
left the production command timeout and process transport unchanged.

## Challenges encountered

The startup marker was present at timeout but carried no timestamp. It therefore
could not distinguish a long endpoint-scan or PowerShell cold start from a stdin
stall by itself. Cross-version ordering and the later passing cases supplied the
discriminating evidence.

## Decisions and alternatives

Rejected changing the production preclosed-stdin implementation because the CI
failures did not demonstrate a transport defect. Rejected an unbounded retry
because it would hide deterministic failures and weaken the release gate. The
60-second allowance stays below the 15-minute matrix-job bound.

## Verification

- Native Windows PowerShell companion and stdin-boundary tests: 8 passed.
- Ruff check and format check for the changed test file: passed.
- Documentation metadata and graph validation: 92 files passed.
- Git whitespace validation: passed.

## Follow-ups

Require both hosted Windows matrix jobs to pass, then merge PR 18 and reconcile
AR-17 and AR-23 with the final worklog and tracker state.
