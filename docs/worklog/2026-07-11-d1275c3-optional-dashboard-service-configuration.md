---
title: "Optional dashboard service and shared configuration"
status: active
category: worklog
created: 2026-07-11
updated: 2026-07-11
tags: [worklog, dashboard, operations, configuration, routing]
related:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: "d1275c37afd5c537768eed0f0eda3715c0ce707c"
short: "d1275c3"
date: 2026-07-11
pr: null
related_issues:
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
---

# Worklog detail: Add optional dashboard service and config parity

## Purpose

Make the installed local dashboard durable on native Windows and Linux while
preserving an explicit installation opt-out. Give operators one safe,
consistent configuration model through both the dashboard and CLI, including
write-only secrets, loopback-only hosts, optimistic revisions, and restart
reporting.

## Approach

Added a current-user Task Scheduler integration on Windows and a `systemd
--user` unit on Linux. The installer starts the dashboard component by default;
`agency install --no-dashboard` skips every service-manager probe and mutation.
Lifecycle commands cover write-free planning, status, install, start, stop,
restart, open, and uninstall.

Both UI and CLI configuration now use one typed, allowlisted transaction that
validates the complete effective configuration before owner-private atomic
replacement. Secrets support preserve, replace, and clear operations without
appearing in read or mutation responses. The dashboard uses authenticated
operations and exact in-page confirmation for sensitive changes.

Service ownership requires both a package marker and an owner-private manifest.
Mutations are serialized, recheck exact task definitions immediately before
Windows operations, preserve prior enabled/running state during rollback, and
compare descriptor PID/token identity before cleanup. Windows uses structured
Task Scheduler COM presence/state probes and explicit XML; Linux preserves
tri-state `systemd --user` results and fails closed when manager state is
ambiguous.

The routing hot path was also tightened after the complete suite exposed a
brittle 32-sample p95. Zero-score agents are sorted only when padding is needed,
and performance gates now use the median p95 from five warmed batches while
retaining aggregate p95, per-batch values, and observed maxima.

## Challenges encountered

- Task Scheduler's default execution limit is finite, so the service needs an
  explicit `PT0S` contract plus bounded restart, battery, idle, identity, and
  least-privilege settings.
- Real Windows probing showed that a missing task is wrapped as
  `DirectoryNotFoundException`, not only `COMException`; absence therefore uses
  a strict HRESULT allowlist rather than localized error text.
- Adversarial review found overwrite/delete races, incomplete XML semantics,
  overstated rollback results, ambiguous Linux state, and descriptor replacement
  races. Each received a focused regression before the full suite was rerun.
- The original p95 measurement was dominated by one or two scheduler pauses;
  repeated measurements confirmed stable central latency and motivated the
  multi-batch gate without weakening thresholds.

## Decisions and alternatives

[ADR-0031](../decisions/0031-optional-user-dashboard-service-and-shared-configuration.md)
records the user-scoped service and shared typed configuration boundary. A
system-wide daemon, raw YAML editor, independent UI writer, and unstructured
localized Task Scheduler parsing were rejected. No real service was registered
or started during verification; deterministic fakes, a native Windows dry run,
and isolated artifact environments preserved the user's machine state.

## Verification

- Full Windows suite: 532 passed, 2 platform-specific skips.
- Critical configuration/dashboard/service/installer/HTTP suite: 208 passed,
  1 platform-specific skip; final service/native subset: 87 passed.
- Routing correctness/evaluation subset: 46 passed; ten repeated evaluations
  passed with stable multi-batch p95 and approximately 22% lower hot-path p50.
- Native Windows service dry run returned `ready_to_install: true`; the exact
  read-only COM probe returned `ABSENT` with exit 0.
- The definitive wheel passed an isolated Windows Python 3.12.10 install and a
  WSL Python 3.12.3 direct-wheel import. Linux lifecycle, rollback, XDG paths,
  0600 state, stale revisions, packaged assets, Windows XML, and structured COM
  contracts passed without real service-manager calls or real-home changes.
- Wheel/sdist content verification, strict Twine, Ruff, JavaScript syntax,
  compileall, high-severity Bandit, strict dependency audit, documentation,
  release hygiene, and Git whitespace checks passed.

## Follow-ups

- Create the same-repository `[AR-13]` tracker issue and write its URL back only
  after explicit authorization for that outward-facing action.
- Live hosted CI and runtime canaries remain part of
  [AR-07](../roadmap/issue-AR-07-public-release-readiness.md); this work does not
  claim that a deterministic service contract is a live host canary.
