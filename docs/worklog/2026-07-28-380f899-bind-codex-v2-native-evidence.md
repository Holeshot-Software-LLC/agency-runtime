---
title: "Worklog detail: Bind Codex V2 hooks to native child evidence"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [codex, hooks, activation, security, canary]
related:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 380f8992fb1d728026be82673bb966a43c148b97
short: 380f899
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: Bind Codex V2 hooks to native child evidence

## Purpose

Repair the installed Codex activation boundary exposed by the failed live
canary: MultiAgentV2 flattens `collaboration.spawn_agent` to
`collaborationspawn_agent`, so the previous exact matcher never injected the
planned specialist context even though Codex spawned the intended child.

## Approach

The installer and runtime now share one anchored allowlist for the legacy and
V2 spellings. A PostTool result can consume a hook-issued activation only after
an atomically unclaimed native-child lifecycle start on the same parent scope.
Bounded JSON parsing retains response identity provenance, V2 requires a rooted
AgentPath whose leaf matches the persisted tool input, response-supplied IDs
must match the lifecycle on first use and replay, and replay is bound to the
exact activation token and tool-use ID. Canary projections preserve the real
process exit code and report which bounded proof surface was unavailable.

## Challenges encountered

Codex reports the child turn rather than the parent trace on `SubagentStart`,
returns its V2 task path as JSON text, and does not expose the spawning tool-use
ID on the lifecycle event. Parent recovery therefore uses an exact active Store
scope plus atomic temporal/cardinality correlation. Independent adversarial
reviews found and closed legacy-name lifecycle gating, JSON-string identity
provenance, replay-lineage, rooted-path, and nested-denial gaps. The remaining
same-account temporal association is explicit in the threat model.

## Decisions and alternatives

Agency stays advisory and does not replace Codex scheduling. Suffix matching,
namespace guessing, synthetic child activation, and accepting a stale isolated
attestation for current-profile verification were rejected. The public canary
now requires the exact existing Store used by the installed hook.

## Verification

- The final named warning-strict production spine passed 536 tests with 5
  platform skips in 82.43 seconds.
- Twelve focused identity, replay, lifecycle, denial, and canary checks passed
  in 34.86 seconds; the final independent security re-review reported no
  AR-191/live-canary blocker.
- All 109 dashboard UI tests and every routing, policy, delegation,
  performance, retrieval-scale, and CLI-startup gate passed.
- Ruff lint/format, metadata, policy, worklog, documentation, and diff checks
  passed. No exhaustive suite or hosted workflow ran.

## Follow-ups

Install this exact checkpoint, renew changed-hook trust, and run one fresh
current-profile activation canary under AR-191 and AR-180. Tracker creation
remains pending explicit outward-write authorization.
