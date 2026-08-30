---
title: "AR-129: Isolate subprocess environments"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [security, processes, installer, delegation, credentials]
related:
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

Shell-free argv and pre-launch executable identity checks are strong, but
ambient credentials outside the selected integration can cross the process
boundary. An unsafe child PATH can also resolve an unintended descendant tool
after the validated launcher starts.

## Approach

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
