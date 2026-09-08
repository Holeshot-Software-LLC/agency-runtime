---
title: "AR-410: Keep Claude transport warm-up outside Agency staffing"
status: in_progress
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [claude, canary, performance, runtime-control]
related:
  - docs/roadmap/handoffs/issue-AR-410.md
  - docs/roadmap/acceptance/evidence/AR-410-claude-warmup-control-20260907.md
  - docs/decisions/0237-isolate-claude-bootstrap-from-agency-evaluation.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-410
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/744
depends_on: []
blocks: []
---

# AR-410: Keep Claude transport warm-up outside Agency staffing

## Problem

The isolated Claude canary uses a first session to initialize freshly installed
plugin hooks. That literal one-word transport warm-up currently runs Agency
staffing. The installed `4db6be16` live attempt spent 89,300 ms in three recorded
warm-up staffing attempts before the real nonce-bound request started. Both
sessions share the same native 180-second deadline.

## Current state

Phase: fast_verification. Source `0e8e9307` and seven regression cases are
checkpointed with ledger `fb3ef70e`. Independent second review reports no
remaining scoped source findings. Tracker #744 exists; isolated acceptance and
changed-candidate native verification are pending. No source verdict is claimed.

## Approach

Apply Claude's supported session-only `--settings '{"disableAllHooks":true}'`
only to the fixed warm-up invocation. Do not pass it to plugin staging or the
actual nonce request. Keep master control, plugin enablement, model profiles,
budgets, permissions, deadline and every strict native proof gate unchanged.
The initial private-master-only approach was discarded after independent review
proved that installed hooks explicitly bind the owner's control path.
Managed policy may override the session setting; do not modify that policy.

## Dependencies

ADR-0237 supplements ADR-0036 and ADR-0158. AR-409's staffing reservation is not
modified. Completion requires isolated acceptance and an installed exact-source
native checkpoint: deterministic tests cannot establish that the host still
activates its second-session hooks after a disabled warm-up.

## Acceptance

- [ ] Only the fixed warm-up receives the supported native hook-disable setting;
  the actual nonce request has no such override, preserves requested authority
  and safe argv/deadline, and leaves owner profiles and control untouched.
- [ ] Failed staging/warm-up or failed private-control projection cannot launch
  an actual request under unverified authority; native-only remains disabled.
- [ ] Existing nonce, accepted-finalization and host-authored child proof gates
  remain unchanged and focused canary regression tests pass.
- [ ] An installed exact-candidate Claude live checkpoint retains the original
  verdict, verifies warm-up isolation and actual-request authority, and proves
  activation only if the existing full native canary succeeds.
