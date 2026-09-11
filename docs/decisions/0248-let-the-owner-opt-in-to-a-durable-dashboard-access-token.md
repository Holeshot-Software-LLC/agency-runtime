---
title: "Let the owner opt in to a durable dashboard access token"
status: accepted
category: decisions
created: 2026-09-10
updated: 2026-09-11
tags: [dashboard, security, operations]
related:
  - docs/roadmap/issue-AR-440-a-stale-hook-runtime-blocks-every-turn-without-naming-itself.md
  - docs/roadmap/issue-AR-436-durable-dashboard-access-without-a-terminal.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0248
type: decision
deciders: [owner]
---

# ADR-0248: Let the owner opt in to a durable dashboard access token

## Status

**Accepted 2026-09-10.** Owner request: the installed dashboard should be
available all the time without a terminal running `agency dashboard service
open`.

## Context

ADR-0029 bound the loopback dashboard to a bearer token carried in the URL
fragment, removed from the visible URL and kept in session storage, and
ADR-0031 made the service durable while keeping the token rotating per
process in an owner-private descriptor. That protects the dashboard from
cross-origin reads and from other local accounts, but it also means a
bookmark stops working at every restart or new browser session, and the
owner needs a terminal to get back in.

## Decision

1. **A config opt-in, off by default.** `dashboard.durable_access: true`
   (schema-validated boolean, restart-bound, settable with
   `agency config set` or `agency dashboard service install --durable-access`,
   which persists it through the locked config transaction before
   installing).
2. **The service reuses one owner-private token.** In service mode with the
   opt-in, the owner bearer is read from
   `~/.agency-runtime/run/dashboard-access.json`, minted once with the same
   hardened, identity-checked publication path as the rotating descriptor,
   and reused across restarts. The rotating descriptor, its lifecycle, the
   broker token, the loopback binding and the origin checks are unchanged.
   Foreground `agency dashboard` still rotates.
3. **The page remembers the token only when told to.** `agency dashboard
   service open` appends `durable=1` to the fragment on the opt-in; the page
   then stores the token in local storage as well as session storage, strips
   the fragment, and later visits read fragment, session storage, then local
   storage. A 401 clears the remembered token so a rotated token is never
   replayed.
4. **Uninstall is the rotation point.** `agency dashboard service uninstall`
   removes the durable token record; the next service start mints a new one
   and one `open` re-teaches the browser.

## Consequences

- With the opt-in, one `open` per browser profile is enough; the bookmark
  then works for as long as the service is installed.
- Residual risk, recorded in the threat model: the token now survives
  process restarts on disk (owner-private, same directory guarantees as the
  descriptor) and in the browser profile's local storage for the
  `127.0.0.1:<port>` origin. Anyone who can read the owner's home directory
  or that browser profile could already read the descriptor or the session;
  the opt-in lengthens the window, it does not widen the audience.
- Off by default, behaviour is byte-identical to before.

## Alternatives

- **A persistent cookie set by the server.** Rejected: it would move the API
  from bearer to cookie authentication and reopen cross-site request
  concerns the fragment design avoids.
- **Show the token on the unauthenticated error page.** Rejected: it would
  hand the token to any page that can reach loopback.
- **Keep rotating and add a desktop launcher that runs `open`.** Rejected by
  the owner's framing: the ask is availability without a terminal or helper.
