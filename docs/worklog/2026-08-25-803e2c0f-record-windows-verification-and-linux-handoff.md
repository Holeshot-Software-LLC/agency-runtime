---
title: "Worklog detail: Record Windows verification and Linux handoff"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [windows, linux, containers, verification, handoff, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 803e2c0f90a274219bab6a05a05b308ed5f387fb
short: 803e2c0f
date: 2026-08-25
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/326
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
---

# Worklog detail: Record Windows verification and Linux handoff

## Purpose

Preserve the exact installed-Windows and repository verification boundary for
the one-install autonomy work, and provide a self-contained Linux prompt that
can close the container and artifact gates without this task's conversation.

## Approach

Reinstall the exact worktree, validate strict assurance and additive recall,
inspect installed host/dashboard state, run deterministic smoke, prove the
explicit prompt CLI against the live Store, and hash-compare the installed
renderer, managed-policy module, and workforce reader with source. Record every
pass, degradation, and non-proof in AR-297, AR-298, the release checklist, and
bounded AR-290/AR-297 recovery capsules.

## Challenges encountered

The controllable dashboard tab's bearer expired before the new prompt and
managed-policy projections could be visually inspected, so that acceptance
item remains open despite exact installed file identity and source UI coverage.
The consumer uv-tool environment also lacks the repository's pytest dependency;
the developer-only decision-conformance command failed there before baseline,
then passed through the repository development interpreter with source
unchanged.

## Decisions and alternatives

No production managed policy was installed on the attended Windows workstation.
Doing so would violate ADR-0173's dedicated-container boundary and would not
prove Linux `/etc` behavior. Deterministic smoke, current files, copied plugins,
Store rows, and model prose remain separate from live host loading and
host-written delivery proof.

## Verification

- The installed prompt command exits 0 with immutable version, standing, hash,
  bounded body/truncation metadata, stored-definition authority, and an explicit
  no-delivery-proof statement.
- Installed dashboard, managed-policy, and workforce-reader SHA-256 values
  match source exactly.
- Installed deterministic smoke passes 8/8 with no runtime drift.
- The named Python production spine passes 840 tests with 20 skips.
- All 138 dashboard UI tests pass.
- Documentation validation passes for 839 Markdown files.
- Routing evaluation passes every threshold.
- Decision conformance passes its baseline and all curated mutations with
  source unchanged.

## Follow-ups

Use the prompt in `docs/roadmap/handoffs/issue-AR-297.md` on the Linux
machine to prove clean Codex, Claude Code, and OpenClaw containers and exact
artifacts. Complete the installed authenticated owner-detail visual check for
AR-298. Tracker creation remains pending explicit authorization.
