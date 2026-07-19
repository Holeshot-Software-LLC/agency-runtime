---
title: "AR-32: Make Windows dashboard task registration natively canonical"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [dashboard, windows, installer, portability, bug]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-32
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/33"
depends_on: []
blocks: []
---

# AR-32: Make Windows dashboard task registration natively canonical

## Problem

The first real default-dashboard install from the reviewed wheel failed on
native Windows. `schtasks /Create /XML` rejected the UTF-8 task file with
`unable to switch the encoding`. After the task file was corrected to UTF-16,
Windows created the task but the installer rejected Task Scheduler's exported
definition because the service canonicalizes the trigger identity, elides
explicit default values, adds the unified scheduling engine value, and inserts
its task URI.

## Current state

Deterministic command-runner tests modeled an exact XML round trip, so they
covered ownership, rollback, and lifecycle behavior without reproducing the
native byte encoding or canonical export. The safety boundary behaved
correctly: it refused to claim ownership or perform an unsafe rollback when the
post-mutation definition did not match its contract.

## Approach

Write a BOM-bearing UTF-16 task file whose declaration matches its bytes. Keep
the stable current-user SID for the principal and resolve the canonical logon
account from that same process-token SID without trusting environment values.
Read Task Scheduler's COM XML through bounded Base64-encoded UTF-8 output so
the inherited console code page cannot corrupt non-ASCII definitions. Parse
only the existing allowlisted Task Scheduler schema, normalize the precise
defaults Windows is allowed to omit, and compare the resulting properties to
the generated definition. Continue to treat ownership markers, semantic
definition equality, and exact pre-mutation requeries as separate checks so
repairable drift remains distinguishable from structural replacement and can
never be started before repair.

## Dependencies

This bug was surfaced by AR-31's real Codex installation gate. It blocks the
default installed dashboard contract on native Windows but does not affect the
explicit `--no-dashboard` opt-out.

## Acceptance

- [x] Task XML bytes carry a UTF-16 BOM and matching declaration.
- [x] The principal retains the current-user SID while the trigger uses the canonical account resolved from that SID.
- [x] Native XML inspection is codepage-independent, bounded Base64/UTF-8 COM transport.
- [x] Native Task Scheduler canonical output remains owned and definition-current.
- [x] Known default elisions normalize without accepting extra triggers, actions, or nested data.
- [x] Semantic drift remains owned and repairable; structural replacement fails closed.
- [x] Start and restart reject semantic drift and revalidate before every native execution mutation.
- [x] Creation, exact requery, run, readiness, rollback, and manifest checks remain bounded.
- [x] A real Windows default install succeeds and the dashboard is reachable after reboot.
- [x] The default-on and `--no-dashboard` contracts remain portable on Windows and Linux.
- [x] Focused, full exact-coverage, package, CI, merge, and tracker validation pass.
