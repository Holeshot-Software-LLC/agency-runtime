---
title: "AR-413 HTTP status propagation and bounded planner reliability repair"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [workforce, transport, receipts, live-evidence]
related:
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues: [docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md, docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md]
---

# AR-413 status propagation and planner reliability

## Purpose

The owner approved planner/gateway configuration changes after two native turns
timed out upstream. Preserve actual HTTP status before further live diagnosis.

## Approach

Add the existing transport status to workforce/hiring attempt records and both
bounded receipt projections. Strict integer100..599 only; absent/zero omitted
for legacy fixed points. No response bodies, headers, endpoints or credentials.
Apply existing ADR-0209, without inference, retry or staffing-policy changes.

## Challenges and alternatives

The live gateway lists133deployments; the planner alias has subscription gpt-5.5
at order1 and existing glm-5-turbo at order2, both45secondtimeouts. Earlier native
activation succeeded through GLM; ordinary turns fail near45.8seconds. Plan one
reversible experiment promoting the existing GLM entry to order0, retaining the
subscription fallback and all other fields. No new provider/key or timeout
increase. Verify readback and ordinary staffing before retaining the change.

## Verification

80 focused tests pass across HTTP-status, staffing-failure, transport-cause and
preflight-diagnosis modules. The new tests cross actual failed workforce turns,
SQLite, routing/operator projection fixed points, hiring and malformed metadata.
Fast Python spine1151passed/3skipped in70.63seconds; dashboard224passed. Ruff
lint passes. Canonical artifact build at716fb04f failed before publication with
release Git output limit; diagnosis pending, no installed proof claimed.

At12:36:01UTC the authorized live gateway PATCH changed only existing GLM planner
deployment ed1b5bbc-bbb7-533a-b3d8-5873a004e4c1 order2 to0. Exact-ID/alias/model
preconditions pass; readback confirms0 and all other deployment parameters
unchanged. The original2 is retained for a scoped inverse PATCH. No service
restart, new key/provider, increased timeout or other alias change.

The next native check uses the existing trusted installed source4cbebf73 (not
the uninstalled status patch) and Codex's built-in approve-for-me reviewer for
the bounded MCP write. This is reviewed approval in workspace-write mode, not
hook-trust bypass or persistent approval reconfiguration. No empty IDs allowed.

## Follow-ups

AR-413 installed failure proof and isolated acceptance; AR-404 native ordinary
staffing/finalization with valid current binding and approved MCP-write mode.
Do not promote the old activation into current ordinary reliability evidence.

Source checkpoint `ed26177f281fba0e4aea807d2092574ea0e47e3d` preserves HTTP status through the full staffing failure path;80focused tests pass. Clean substantive/ledger pair precedes the authorized gateway experiment.

Pre-live checkpoint `0c240444ce167c0ca34054b38b65a31d7950913c` records the reversible order-only planner experiment and successful fast verification. Native runtime remains the trusted prior payload; artifact build is blocked on a bounded Git output diagnostic.
