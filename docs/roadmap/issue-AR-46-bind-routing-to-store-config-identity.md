---
title: "AR-46: Bind routing surfaces to the Store configuration identity"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-19
tags: [routing, configuration, adapters, dashboard, embedding]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-46
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/47"
depends_on:
  - AR-40
  - AR-44
blocks:
  - AR-47
  - AR-49
---

# AR-46: Bind routing surfaces to the Store configuration identity

## Problem

Preflight and route-explanation surfaces load process-default configuration when
no config object is passed, even when their Store is explicitly bound to a
different config. Hermes, embedded adapters, HTTP/MCP, and the dashboard Route
Lab can therefore select with one policy while persisting to another identity.
LiteLLM callbacks have the same split for enablement, skipped models, privacy,
and preflight/router settings when a custom-bound Store is supplied alone. A
long-lived callback can also freeze its construction-time config, allowing an
agent disabled from the CLI or dashboard to remain routable until process
restart.

## Current state

The implementation now captures one Store-bound config and disabled-agent
snapshot for the public runtime, preflight, HTTP, MCP, dashboard, and adapter
routing paths. The dashboard binds each routing operation to its active Store
and config revision. Omitted callback configuration refreshes from that same
bound file, while explicitly supplied callback configuration remains immutable.

## Approach

Use explicit typed config first, otherwise load from `store.config_path` when
present, and retain process-default behavior only for unbound Stores. Apply the
same rule to preflight, route explanations, and adapter entry points so every
host and dashboard path shares one policy snapshot. Dashboard routing holds the
config read lock while it verifies active-versus-desired Store binding, captures
the config/catalog pair, and publishes revision evidence; Store drift is a
restart-required failure, not a mixed snapshot. Long-lived callbacks keep the
immutable Store/config path binding but refresh omitted configuration through
the file-aware cache for each event; an explicitly supplied config remains
intentionally immutable.

## Dependencies

AR-40 binds dashboard handlers, and AR-44 binds Store storage. This completes
the routing layer under ADR-0006 and the turn recipe contract in ADR-0045.

## Acceptance

- [x] Bound Store config governs preflight and route explanations when config is omitted.
- [x] Explicit config retains precedence and unbound behavior remains compatible.
- [x] Hermes, LiteLLM, dashboard Route Lab, HTTP/MCP, and embedded adapter paths cannot consult a poisoned process default.
- [x] Long-lived LiteLLM callbacks apply agent disables, adapter enablement, skip-model, and capture-policy changes on the next event without process restart.
- [x] Explicit callback configuration remains immutable while omitted configuration remains live and Store-bound.
- [x] Ready recipe fingerprints and disabled-agent policy use the same bound snapshot.
- [x] Full exact-coverage, Windows/Linux, package, and tracker gates pass.
