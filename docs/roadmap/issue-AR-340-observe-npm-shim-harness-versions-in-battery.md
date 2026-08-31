---
title: "AR-340: Observe npm command-shim harness versions in the battery"
status: done
category: roadmap
created: 2026-08-31
updated: 2026-08-31
tags: [reliability, windows, battery, codex, claude]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/handoffs/issue-AR-338.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-340
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/373
depends_on: []
blocks: [AR-338]
---

# AR-340: Observe npm command-shim harness versions in the battery

## Problem

`agency battery --baseline` silently adopts nothing on Windows.
`observe_harness_version` resolves each harness executable with
`shutil.which`, which on Windows returns the npm command shim (for example
`C:\agency-cli\claude.cmd`), and then executes `("claude", "--version")`
through the bounded no-shell runner. CreateProcess cannot launch a `.cmd`
directly, the execution raises, the exception is swallowed, and the host is
skipped. With every host skipped the command exits 0 with an empty baseline,
so the AR-337 change trigger can never observe a version change on Windows,
and the gap is visible only in doctor's "no battery baseline recorded" rows.

## Current state

Measured 2026-08-31 during the AR-338 Windows bring-up:
`agency battery --baseline --json` returns `{"baseline": {}}` with exit 0
while `claude` 2.1.250 and `codex-cli` 0.150.1 are both resolvable on PATH
from `C:\agency-cli` (as `.cmd` shims). Receipt:
`~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`
(`defects_found.battery_baseline_shim_blindness`). The battery core is
otherwise cross-platform; its trigger service remains systemd-only with the
Windows scheduled-task analog tracked under AR-337.

## Resolution (2026-08-31)

Fixed on the filing day. `observe_harness_version` now freezes the version
probe through `prepare_process_argv` -- the same shim-aware executable trust
walk the canary launch path uses -- so npm `.cmd` shims resolve to their
native executable or `node` plus the allowlisted CLI script.
`record_baseline` reports every unobservable host under `skipped` with a
names-only reason, and `agency battery --baseline` exits nonzero when
nothing was adopted. Live on the AR-338 Windows machine: the baseline
adopted `claude 2.1.250 (Claude Code)` and `codex-cli 0.150.1` with
hermes/openclaw skipped as `command not discovered`, and the pre-fix
0abe4a77 runenv's `agency doctor` reads the recorded rows green, proving
the fingerprint file contract across versions. Receipt:
`~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`
(`fixes_verified_20260831.ar340_battery_shim_observer`).

## Approach

Resolve npm command shims to their underlying `node.exe` plus `cli.js`
identity the way the host canary launch path already does, keeping the same
executable-trust walk over the resolved artifacts. Additionally, make an
empty adoption loud: when `--baseline` adopts zero harnesses the command
should exit nonzero and say which hosts were skipped and why, instead of
reporting silent success.

## Dependencies

None. The observer fix reuses the existing shim-resolution and trust
machinery; the loud-empty-adoption change is local to the battery CLI.

## Acceptance

- [x] On Windows, `agency battery --baseline` adopts observed versions for
      every installed battery harness whose CLI is an npm command shim.
- [x] Doctor's battery rows report the recorded baseline on the AR-338
      Windows machine.
- [x] `--baseline` with zero adoptable harnesses exits nonzero and names
      the skipped hosts with reasons.
- [x] The version observation path still refuses executables that fail the
      executable-trust walk.
