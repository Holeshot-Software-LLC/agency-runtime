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
commit: c1e17448f7107ae94a6c35276e42e965a921b3cb
short: c1e17448
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/766
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

Final branch checks pass:1314Markdown files, policy availability,2184 exact
substantive worklog rows, strict tracker parity404items with2historical PR skips,
Ruff lint and776formatted source files, diff cleanliness. No runtime source was
changed, so the prior exact-source1151/3skip Python spine,224dashboard and8smoke
results are reused; no new unit-test pass is claimed. Fresh live results below
remain mixed and independently determine the outcome.

The linked receipt records eight trusted hooks, fresh eight-tool MCP/status,
two launcher probes and native version. First current-profile activation passes
without bypass: accepted staffing, completed native child, accepted finalization
and persisted attestation. It takes129.6seconds, including97.454second staffing
with one candidate-contract retry. Two ordinary native turns fail at the planner
after45.8seconds HTTP errors; public MCP status and host-status pass, finalizer
is not accepted. Native read-only/never approval is an explicit limitation.
AR-413/#765 tracks the status that the workforce attempt discards after the
transport captured it. Gateway timestamp-correlated evidence supports an upstream
timeout; no route or gateway service was changed.

## Follow-ups

Diagnose the existing planner route without altering it; obtain explicit scope
before provider/gateway changes. Preserve HTTP status through AR-413's complete
receipt path. Only then retry a valid-bound ordinary staffed/finalized turn in an
approved native MCP-write mode and measure repeatability. No OpenClaw restart or
wide backlog work. The install refresh did restart its default optional dashboard.

Pre-live checkpoint `2c07c6539a0acfcd943ac85256d07f9d3d204731` records the owner launch repair, fresh trusted hooks and independent MCP startup. Native execution remains pending; this clean recovery pair precedes live evaluation under the context protocol.

Activation checkpoint `60ccac3128d2746281c01989cd7260b6a4dae4e5` records the first normal trusted Codex activation, accepted native execution/finalization and exact latency. Ordinary MCP proof remains pending.

Ordinary-run checkpoint `c1e17448f7107ae94a6c35276e42e965a921b3cb` records working native MCP reads, two planner HTTP failures and the finalizer test's approval/binding limitations. AR-413/#765 preserves the downstream diagnostic follow-up. No ordinary reliability pass or latency improvement is claimed.

PR [#766](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/766) merged as `fce1726ed869a3e83f4902c75f5fa9da77c9873f` on main at2026-09-08 11:43:59UTC. The launch repair and exact successful/failed native observations are now durable. AR-404 stays in progress and AR-413 stays open. Source payload and trusted hook projection remain unchanged.
