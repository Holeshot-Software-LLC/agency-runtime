---
title: "Accept stopped OpenClaw uninstall status"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-09-05
tags: [openclaw, uninstall, gateway, compatibility]
related:
  - docs/roadmap/acceptance/issue-AR-271.md
  - docs/roadmap/acceptance/evidence/AR-271-stopped-uninstall-20260905.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/installer_uninstall.py
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-271
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-271: Accept stopped OpenClaw uninstall status

## Problem

OpenClaw `gateway status --deep --require-rpc --json` returns exit 1 when the
gateway is stopped and places the authoritative stopped facts in nested service
state. The install classifier now accepts that exact bounded shape under
AR-285, but the separate uninstall classifier still requires exit 0 and
top-level status, so safe rollback is blocked even after a native stop.

## Current state

2026-09-05: reproduced against main 78e501b7. An offline production-function
replay sends the same exact stopped receipt to both paths: installation returns
False (stopped), uninstall returns None (unknown), with zero native commands.
The regression-first tests produce seven failures and fifteen passes before
the repair; all seven failures are the expected refusal of the stopped receipt.
The bounded package extracts the existing install classifier and uses it from
uninstall, leaving native runners, immutable execution binding, owner authority,
locked replanning, retained backups and native postconditions in place.
Focused demo: 248 tests passed, two Windows-only skips in 7.38s, including
owner denial and launcher/environment/revalidation drift refusal. Phase:
fast_verification. All three isolated Codex criteria are satisfied against
candidate 4fdcd6a7; protected conformance and PR #679 delivery remain pending.
The legacy null tracker URL remains pre-tracker history.

Historical incident:

The post-plugin-removal dry-run is preserved as
`OpenClaw gateway state is unproven; uninstall is blocked`. Systemd separately
proved the unit inactive. Recovery invoked the checked-in transactional
prior-delivery restore only after proving both gateway inactivity and plugin
absence; all five retained streaming values were restored and verified.

## Approach

Share or mirror the bounded stopped-state classifier used by installation.
Accept only complete, untruncated exit-1 receipts whose nested runtime state is
exactly stopped/inactive/dead. Keep live, partial, ambiguous, truncated, and
unknown receipts blocked.

## Dependencies

- AR-285 stopped-gateway classifier contract.
- Existing uninstall execution binding and final-state verification.

## Acceptance

- [ ] Installation and uninstall share the bounded gateway classifier: complete exit-1 stopped/inactive/dead receipts prove stopped, and successful legacy top-level stopped/live behavior is preserved.
- [ ] Malformed, partial, ambiguous, truncated, contradictory/live and other nonzero receipts cannot authorize uninstall; blocked plans execute no native mutation and leave the owned files unchanged.
- [ ] Disposable-home contract tests prove write-free planning and reversible owned-bundle retirement for a stopped gateway, with and without native plugin registration; owner approval, execution identity and final state revalidation remain enforced, and live/unknown drift after approval or immediately before commit blocks mutation. No real gateway restart or live uninstall is claimed from these tests.
