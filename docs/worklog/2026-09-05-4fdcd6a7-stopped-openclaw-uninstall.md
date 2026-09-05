---
title: "AR-271 stopped OpenClaw uninstall classification"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [uninstall, openclaw, regression, backlog]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/acceptance/issue-AR-271.md
  - docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4fdcd6a7b1ff3ae3ab8a666937adeb5d1111895b
short: 4fdcd6a7
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/679
related_issues:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog: share stopped gateway classification with uninstall

## Purpose and approach

An older uninstall-only parser rejected OpenClaw's stopped exit-1 receipt after
the installer already handled it. Extract the existing install interpretation
without changing it and call that single function from both paths. Keep the
bound native runner and every owner/ownership/execution/retention postcondition.
The original issue had no acceptance checklist, so make its existing bounded
goal and preserved safety requirements explicit before isolated verification.

## Challenges and alternatives

The new regression failed seven cases before the code repair; fifteen negative
cases already passed. Mirroring another copy of the parser would leave the
same drift risk. Bypassing nonzero probes wholesale or running a real uninstall
would expand authority unnecessarily. Contract tests instead use disposable
homes and injected native replies, including changes at both final safety gates.
The umbrella capsule is refreshed as a bounded current-state projection; exact
historical evidence remains in its canonical issue and earlier worklog records.

## Verification

Focused installer/uninstall/CLI: 248 passed, two Windows-only skips (7.38s).
Named production spine: 1030 passed, three skips (63.79s). UI: 138 passed.
Ruff, format, metadata, policy, strict docs and diff checks pass. Acceptance and
protected decision conformance were pending at implementation. Candidate
4fdcd6a7 now has three isolated satisfied criteria, preserved in 8421e5f7;
final conformance and PR #679 delivery remain. No real host was uninstalled or
restarted, no trust bypass or credential change occurred, and no exhaustive
workflow was dispatched.

## Follow-ups

Freeze the candidate, run three isolated checks, complete final conformance,
merge through a PR and record the exact installed-source smoke. AR-285 retains
its separate historical receipt gap; AR-348/349 retain hiring-safety work.
