---
title: "Worklog detail: Checkpoint exact Codex child-judge blocker"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, containers, evidence, native-child]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 2fa5013fc96174195a21fd998571bb6cb20e20f5
short: 2fa5013f
date: 2026-08-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
---

# Worklog detail: Checkpoint exact Codex child-judge blocker

## Purpose

Record the immutable `3e42598d` artifacts and the first two rebuilt Codex
production-container attempts before another live evaluation.

## Approach

Built and independently verified the exact wheel/source pair, bound the wheel
into Codex 0.149.1, and proved fresh absence separately in C1 and C2. C1 stopped
at planner semantics. C2 accepted the fixed route, completed the real child,
and persisted native-child decision `1d351ac6...c63082` only after the repaired
install-identity boundary and stable routing-state checks.

## Challenges encountered

The configured free child judge failed unavailable after 26,341 ms, so Agency
correctly withheld the v6 card. The 180-second outer canary then expired about
five seconds after child completion, leaving no finalization or attestation.

## Decisions and alternatives

No config, model, trust, or policy decision changed. The next bounded package
diagnoses the exact approved judge route and uses the supported 600-second
activation timeout in a fresh container. Bypass and false-delivery claims remain
prohibited.

## Verification

- Build, strict Twine, independent distribution verification, two container
  starts, two private auth copies, and two absence receipts exit 0.
- C1 and C2 installer exits are exactly 1 with empty stderr and retained
  mode-0600 receipts, Stores, and rollouts.
- All 870 documentation validations and `git diff --check` pass.
- Package-end telemetry records 36.1 percent remaining and requires this clean
  checkpoint.

## Follow-ups

- Restore the exact free child-judge route and prove a complete Codex
  no-bypass attestation under AR-297.
- Continue the remaining harness, ordinary-process, host/dashboard, gate, and
  teardown packages from the canonical capsule.
