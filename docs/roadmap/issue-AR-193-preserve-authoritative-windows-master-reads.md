---
title: "AR-193: Preserve authoritative Windows master reads for UAC-filtered owners"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [windows, security, controls, dashboard, canary]
related:
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - agency_runtime/core/runtime_control.py
  - agency_runtime/core/canary.py
  - agency_runtime/server/dashboard.py
  - tests/test_runtime_control.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-193
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-185, AR-192]
---

# AR-193: Preserve authoritative Windows master reads for UAC-filtered owners

## Problem

The Windows token probe treats `TokenHasRestrictions` as sufficient evidence
that a process must use the reduced-privilege master-control reader. Normal
medium-integrity owner shells can set that bit solely because UAC marks the
Administrators group deny-only. Those shells still have legitimate owner rights
to the private control path, so the reduced reader correctly rejects them as
mutable and falls back to the dashboard. If the dashboard is unavailable,
enforcement then fails enabled instead of reading a valid global `OFF` state.

## Current state

Exact installed revision `8118b8d` reported the fail-enabled generation-zero
default while the strict reader safely returned the real owner-private
generation-28 document. The token had no restricting SID and was not an
AppContainer, but `TokenHasRestrictions=true`; all negative mutation probes
were correspondingly true because this was the legitimate owner. The dashboard
descriptor was stale and its process absent, exposing the classification bug
before any model invocation. No cross-account write, reparse-point, or DACL
weakness was found. Tracker creation remains pending explicit authorization.

The implementation now tries the strict reader first, retains the exact
restricted fallback only after a strict security refusal, threads uncached
reads through the reduced path, and makes the dashboard master endpoint read
uncached. The source candidate returned the real generation-28 document through
the direct transport. The full 108-test control module, four changed dashboard
boundary tests, the named 536-test production spine, lint/format, documentation,
UI, and routing gates pass. Exact installed-package and live-canary proof remain
pending.

## Approach

Keep the strict owner-private reader primary for the canonical identity. Only
after it raises a security error may a positively restricted Windows caller use
the existing reduced reader and authenticated dashboard recovery. Preserve the
reduced reader's stable-identity and negative-mutation proofs. Thread explicit
uncached reads through both reduced and dashboard paths so a live canary cannot
reuse a prior master generation.

## Dependencies

ADR-0058 and ADR-0060 require direct owner-private access to remain primary and
limit dashboard brokerage to restricted callers. AR-185 and AR-192 depend on a
fresh authoritative master snapshot before their current-profile canary may
invoke Codex.

## Acceptance

- [x] A UAC-filtered owner token whose strict read succeeds returns the exact
  persisted document without consulting the reduced reader or dashboard.
- [x] A strict security failure may recover only through the existing
  positively restricted, negative-mutation-proven reader and bounded dashboard
  broker.
- [x] `use_cache=False` bypasses the direct and reduced-reader caches, and the
  dashboard master endpoint performs an uncached authoritative read.
- [x] Focused Windows/control tests prove exact generation preservation,
  global-`OFF` enforcement, broker fallback, and fail-closed malformed paths.
- [ ] The exact installed candidate reads the real master generation and a
  bounded Codex activation canary proceeds past readiness without a dashboard.
