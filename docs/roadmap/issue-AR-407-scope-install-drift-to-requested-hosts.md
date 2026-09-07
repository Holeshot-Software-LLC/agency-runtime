---
title: "AR-407: Scope install drift warnings to requested hosts"
status: done
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [install, drift, diagnostics, hosts]
related:
  - docs/roadmap/acceptance/issue-AR-407.md
  - docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md
  - docs/roadmap/issue-AR-258-reconcile-the-installed-projection.md
  - docs/roadmap/issue-AR-363-deployed-fix-witness-manifests.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - agency_runtime/cli/install_commands.py
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-407
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/727
depends_on: []
blocks: []
---

# AR-407: Scope install drift warnings to requested hosts

## Problem

A successful Codex-only refresh warns that its hooks did not pick up the CLI
source even when the reported stale projection belongs only to OpenClaw.
The installer takes the first drift report across all recorded hosts instead
of scoping its residual warning to the requested installation targets.

## Current state

September 7 live refresh returns zero and runtime-verified for Codex. Its
per-host pointer, marketplace hooks and current plugin cache pin 4329d76058d1
from the AR-348 package. Only OpenClaw pins 1d617ca589a2 from AR-271.
The residual warning therefore misattributes unrelated host drift.

The current parent separately retains older cached hooks and lacks the
configured client variable in its launch environment. Correcting a warning
does not fix either condition or establish current-turn staffing.

The bounded implementation now passes resolved targets into the residual
projection helper. Global status is unchanged. Thirty-five regressions cover
text/JSON, same/foreign packages, explicit/default/all/empty resolved scopes,
selected drift and advisory failures. Two existing doubles assert the exact
targets. Focused combined validation passes 158 cases with one Windows-named
deselection; independent focused review reports no finding and 35 passes.
Actual mixed-pointer validation now passes with all five pointer bytes and
metadata unchanged. Clean ef6523b3 produces the portable pair under umask 077;
independent verifier and strict Twine pass. Fresh installed CLI/MCP/dashboard
smoke passes and all-host generated smoke passes eight/zero/zero in 5.09s.
These are scoped real installed checks, not a new native model-turn canary.
All three isolated criteria satisfy at dcd58720; no requirement changed.

## Approach

Filter install residual drift to resolved installation targets. Keep global
status and its complete cross-host drift list unchanged. Exercise text/JSON,
requested-host drift, unrelated-host drift and multi-target behavior.
Verify against the actual mixed installed pointers without replacing OpenClaw.

## Dependencies

Existing per-host projection authority (AR-258) and witness evidence (AR-363).
No new credential loading, trust bypass, gateway restart or Windows execution.

## Acceptance

- [x] A single-host install excludes unrelated hosts from residual drift text and JSON while retaining relevant requested-host drift.
- [x] Multi-target install retains drift for its resolved targets and global status still reports all recorded-host drift.
- [x] Focused regressions and an exact-source check against the live mixed-host installation demonstrate the correction without modifying unrelated hosts or credential/trust policy.
