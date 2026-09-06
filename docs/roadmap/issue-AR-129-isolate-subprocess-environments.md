---
title: "AR-129: Isolate subprocess environments"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-05
tags: [security, processes, installer, delegation, credentials]
related:
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/process_environment.py
  - tests/test_subprocess_environment_security.py
  - docs/THREAT_MODEL.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
  - agency_runtime/core/installer.py
  - agency_runtime/core/delegation
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-129
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-129: Isolate subprocess environments

## Problem

Installer probes copy the complete parent environment into third-party host
CLIs, and delegated backends can retain dot, relative, repository, or caller
supplied executable-search entries.

## Current state

**2026-09-05 oldest-first disposition: implemented, retain the Windows evidence
hold for the owner.** At reviewed main 66282312, installer_native's
`_command_environment` and delegation/backend_security's `delegation_environment`
both call `least_privilege_subprocess_environment`. The builder starts from
an explicit allowlist, selects only its integration home, removes unsafe ambient
PATH entries and rejects unsafe explicit entries. This is not an unimplemented
environment-isolation feature to rebuild.

The non-Windows environment/executable-discovery/namespace package passes
**64 tests, 12 Windows-named cases deselected, in 0.43s**. Sentinel unrelated
credentials are omitted, selected-host/proxy/locale values survive, and empty,
dot, relative, missing and repository PATH entries are rejected or filtered.
Tests use synthetic sentinels; no real credential value was read or printed.
This verifies the tested POSIX/source boundaries, not native Windows behavior.
No runtime code, original acceptance item or host configuration changes.

The explicit Windows/POSIX acceptance item prevents a full completion claim
from this Linux-only pass. The owner reserved Windows work for their machine;
leave that evidence hold visible and proceed to AR-130 after this disposition
merges. AR-129 is exempt pre-tracker history, so no duplicate tracker is created.
The old full-release-gate wording below is not a reason to run an exhaustive
corpus: ADR-0105 governs bounded verification; Windows and relevant installed
evidence still require their actual proof.

### Historical pre-implementation assessment

Shell-free argv and pre-launch executable identity checks are strong, but
ambient credentials outside the selected integration can cross the process
boundary. An unsafe child PATH can also resolve an unintended descendant tool
after the validated launcher starts.

## Approach

Current remaining handoff: on the owner's Windows machine, run the environment,
executable-discovery and executable-namespace modules natively, retaining exact
interpreter/platform/source identity and results; verify relevant installed
child behavior with sentinel values only. Then build the normal isolated
acceptance record before considering completion. Do not weaken PATH/credential
boundaries or infer a Windows pass from platform simulations on Linux.

Historical implementation plan:

Build all child environments from a documented allowlist, pass only the
selected integration's credential/home variables, and canonicalize PATH with
the same absolute non-repository rules used for launcher discovery. Reject an
unsafe explicit override instead of silently preserving it.

## Dependencies

ADR-0091 defines the cross-platform process environment contract.

## Acceptance

- Sentinel unrelated credentials never reach installer or delegated children.
- Empty, dot, relative, and repository PATH entries never reach children.
- Required platform, proxy, locale, and selected-host variables remain usable.
- Windows and POSIX tests prove the exact child environment and executable
  resolution behavior.

## Implementation evidence

Installer and delegated children now share one least-privilege environment
builder. Ambient unrelated credentials and cross-host auth roots are removed,
PATH is canonicalized to existing absolute non-repository directories, unsafe
explicit overrides fail closed, and delegated processes receive private
HOME/TEMP roots. Focused process suites and the combined checkpoint suite pass.
The item remains open until the full release gate and fresh installed-host
smoke complete.
