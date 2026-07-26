---
title: "AR-142: Instrument runtime boundaries and hiring outcomes"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [observability, http, mcp, hooks, sqlite, hiring]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - agency_runtime/server
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/selector/receipt_projection.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-142
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-142: Instrument runtime boundaries and hiring outcomes

## Problem

HTTP, dashboard, MCP, hook, and Store boundaries do not share one safe request
identifier, duration, outcome class, and failure reason. Several hook
correlation/consumption failures collapse silently to pass-through, and hiring
decisions are absent from durable routing receipt projection.

## Current state

Canonical trace IDs exist in evidence tables for post-hoc analysis, but live
support cannot reliably connect a browser error or MCP failure to one bounded
server/Store event. Logging payloads or bearer tokens would be unacceptable.

## Approach

Define one content-free observation envelope with a random request ID, hashed
correlation, surface, operation, bounded reason code, latency, outcome, Store
generation where relevant, and no prompt/token/path content. Persist or emit
hiring created/declined/no-attempt outcomes in the authoritative route receipt.

## Dependencies

AR-132 defines hiring semantics. AR-136 defines planned-child failure reasons.

## Acceptance

- UI, HTTP, MCP, hooks, and Store logs correlate one request without payloads.
- Slow queries and lock/busy outcomes are measurable without SQL values.
- Silent planned-hook failures become bounded deny/pass-through observations.
- Every route receipt contains a truthful hiring outcome.
- Logs redact control characters, tokens, prompt text, credentials, and private
  filesystem paths; retention remains finite and documented.

## Implementation evidence

A strict content-free observation envelope now covers browser/dashboard, HTTP,
MCP, hook, and slow/error Store boundaries with a random request ID, hashed
correlation, fixed operation/outcome/reason labels, duration, and optional Store
generation. Dashboard responses echo X-Agency-Request-ID; untrusted request
targets and exception messages do not enter fault logs. Every normalized route
receipt projects a truthful created, declined, mixed, or no_attempt hiring
outcome. Redaction, nested correlation, slow/locked SQLite, HTTP, MCP, hook,
dashboard, and receipt tests pass. Troubleshooting documentation states that
envelopes are ephemeral standard logs unless an operator configures an
external finite-retention sink; durable Store evidence retains its configured
finite policy.
