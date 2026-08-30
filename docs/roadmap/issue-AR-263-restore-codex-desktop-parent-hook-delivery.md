---
title: "AR-263: Restore Codex Desktop parent hook delivery"
status: open
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [codex, desktop, hooks, activation, observability, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-263
priority: p0
tracker_url: null
depends_on: [AR-199]
blocks: [AR-119]
---

# AR-263: Restore Codex Desktop parent hook delivery

## Problem

Codex Desktop can start or resume a task with Agency's plugin enabled and all
hook state trusted while dispatching no current `SessionStart` or
`UserPromptSubmit` lifecycle event. The model then receives no Store-backed
Agency snapshot. Rendering `Agency/Agencies loaded: none` in that state hides
an activation failure as a legitimate empty staffing result.

## Current state

- Codex Desktop package `26.818.3698.0`, using embedded CLI
  `0.149.0-alpha.4`, reports hooks stable and the current Agency plugin enabled.
- The installed plugin manifest contains the expected lifecycle hooks, and the
  owner configuration marks each current hook state trusted and enabled.
- The active task's session record contains no injected Agency snapshot or
  delegation plan. The hook log contains no current-task `SessionStart` or
  `UserPromptSubmit`, and the Store has no current run or resident-manager
  binding for this task.
- A second completely new Desktop task,
  `01a02587-1489-7e13-834e-3299ae05fb43`, began at `2026-08-21T18:13:24Z`
  after the exact-main install. Its first assistant response again contained no
  Agency or skill header. The hook log had not advanced since
  `2026-08-21T17:52:11Z`, and the Store contained zero runs, resident-manager
  bindings, or skill rows for either the task or turn ID. The intended exact
  `agency status` control was not actually the first user turn, so this is a
  repeated lifecycle-dispatch observation rather than that exact prompt proof.
- A fresh Codex CLI control already proved the parent path: it loaded
  `agency-steward` and emitted the exact Store-backed header. That evidence is
  retained and is not generalized to the Desktop frontend.
- Open upstream Codex reports 21639 and 33413 describe the same
  frontend/embedded-runtime boundary; they are corroborating context, not a
  repository dependency.
- No provider call or child draw was made while diagnosing this failure.
  Provider routing is not implicated, and no AR-119 matrix cell moved.

## Approach

Keep the CLI parent proof and the Desktop failure separate. Do not fabricate a
header from model memory, change provider routing, or spend a live draw. Require
a current host lifecycle event and Store binding before an Agency-loaded claim
is valid. When the authoritative snapshot is absent, expose activation as
unavailable instead of projecting `loaded: none`. Track the upstream Desktop
dispatch defect and validate any supported host-side repair with a no-provider
parent-only control.

## Dependencies

- AR-199 owns the established Codex workforce/header evidence contract.
- AR-119 needs truthful per-harness parent activation before Codex Desktop can
  contribute new live evidence.
- Upstream Codex Desktop owns lifecycle dispatch before Agency's hooks can run.

## Acceptance

- [ ] A fresh Codex Desktop task dispatches both current `SessionStart` and
      `UserPromptSubmit` hooks from the enabled, trusted Agency plugin.
- [ ] The Store records the current run and resident-manager binding.
- [ ] The injected snapshot and exact final header name `agency-steward` for a
      parent-only control, with no provider draw required.
- [ ] The existing Codex CLI parent control remains green.
- [ ] Missing authoritative context is reported as activation unavailable,
      never as `Agency/Agencies loaded: none`.
- [ ] Exact merged installation is rechecked without promoting a rule or
      moving an AR-119 matrix cell.
- [ ] A same-repository tracker issue is created after explicit authorization.
