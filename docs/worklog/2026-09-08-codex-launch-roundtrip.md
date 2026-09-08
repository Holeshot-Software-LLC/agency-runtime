---
title: "AR-404 repair owner Codex launch and prove native roundtrip"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [codex, launch, native, credentials]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-codex-roundtrip-20260908.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues: [docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md]
---

# AR-404 Codex launch and native roundtrip

## Purpose

Deliver the owner's requested working Codex session before more backlog work.

## Approach

Inspect fresh trust and installed MCP startup independently. Provision the
existing credential at the owner launch boundary, retain native subscription
login and routing, then use normal native verification. Product code and
generated hook hashes stay unchanged; no credentials are copied or replaced.

## Challenges and alternatives

The old conversation is unstaffed and disconnected, but that does not prove a
broken fresh server: actual startup passes. Do not put keys in plugin manifests,
add product secret-file fallback, replace routes or grant trust programmatically.

## Verification

The linked receipt records eight trusted hooks, fresh eight-tool MCP/status,
two launcher probes and native version. First current-profile activation passes
without bypass: accepted staffing, completed native child, accepted finalization
and persisted attestation. It takes129.6seconds, including97.454second staffing
with one candidate-contract retry. Ordinary MCP-backed proof remains pending.

## Follow-ups

Complete current-profile native roundtrip, then bounded ordinary MCP/finalization
and latency checks. Stop at explicit operator prerequisites; no OpenClaw restart
or wide backlog work.

Pre-live checkpoint `2c07c6539a0acfcd943ac85256d07f9d3d204731` records the owner launch repair, fresh trusted hooks and independent MCP startup. Native execution remains pending; this clean recovery pair precedes live evaluation under the context protocol.
