---
title: "AR-436: Durable dashboard access without a terminal"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [dashboard, security, operations]
related:
  - docs/decisions/0248-let-the-owner-opt-in-to-a-durable-dashboard-access-token.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-436
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/856
depends_on: []
blocks: []
---

# AR-436: Durable dashboard access without a terminal

## Problem

The dashboard service is already durable (a per-user systemd unit), but its
access token rotates with every process and the page keeps it only in session
storage. A bookmarked `http://127.0.0.1:7810/` therefore shows "This dashboard
URL has no active access token" after any restart or new browser session, and
the only way back in is a terminal running `agency dashboard service open`.
The owner asked on 2026-09-10 for an install-time opt-in that makes the
dashboard durable and available all the time.

## Current state

Implemented on branch `claude/ar436-dashboard-durable-access-20260910` per
ADR-0248: `dashboard.durable_access: true` (or
`agency dashboard service install --durable-access`) makes the service reuse
one owner-private token stored at `~/.agency-runtime/run/dashboard-access.json`
across restarts; `agency dashboard service open` then appends `durable=1` to
the fragment and the page remembers the token in the browser profile, so the
plain bookmark works afterwards; a 401 forgets the remembered token; `agency
dashboard service uninstall` removes the durable token and is the rotation
point. Off by default, nothing changes.

## Approach

Keep the bearer model, the loopback-only binding, the origin checks and the
owner-private descriptor exactly as they are; change only where the token
comes from (a persisted owner-private record when opted in) and where the page
keeps it (local storage instead of session storage when told to). Document the
residual risk in the threat model.

## Dependencies

ADR-0029 and ADR-0031 own the dashboard's security and service model.

## Acceptance

- [ ] With the opt-in, two consecutive service starts publish the same owner
      token, the token file is owner-private, and without the opt-in the
      token still rotates and the file is untouched.
- [ ] `agency dashboard service open` marks the fragment durable only on the
      opt-in, never prints the token, and the page persists and later reads
      the remembered token, forgetting it on a 401.
- [ ] `agency dashboard service install --durable-access` persists the config
      setting through the locked transaction, `uninstall` removes the durable
      token, and after a reinstall of the runtime the live service is
      reachable from a plain bookmark after one `open`.
