---
title: "Worklog detail: Project effective inference topology"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [dashboard, inference, configuration, delegation]
related:
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 05291b0ecfdb1403b56ab9682d7fa04a0eb3648e
short: 05291b0e
date: 2026-08-25
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/326
related_issues:
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Project effective inference topology

## Purpose

Make the authenticated dashboard truthfully show the named providers and routes
that actually own inference on the current installation, including assurance,
dense recall, Jina embedding/reranking, model thinking levels, judge roles, and
the native-host delegation boundary.

## Approach

Materialize one read-only Settings panel from the already-redacted effective
configuration. Render bounded global and harness routes plus named profile
facts with sanitized endpoint identity and write-only secret handling. Relabel
the old judge surface as a legacy fallback and state that Agency inference owns
staffing while each native harness owns child spawn and execution.

## Challenges encountered

The first release-asset check correctly rejected the new 385,530-byte dashboard
against the prior audited ceiling. The feature uses existing CSS primitives and
retains readable branch-tested JavaScript; the ceiling moved only to 377 KiB,
leaving 518 bytes (0.13 percent) of headroom.

## Decisions and alternatives

No new architecture was introduced. The projection follows ADR-0118,
ADR-0138, ADR-0153, and ADR-0171. Editing the minified HTML or showing only the
raw JSON was rejected because either would weaken maintainability or preserve
the consumer-facing ambiguity. Secret values and URL credentials/query strings
never render.

## Verification

- All 138 dashboard UI tests pass.
- Dashboard coverage passes at 96.92 percent lines, 86.74 branches, and 95.71
  functions.
- The exact 385,530-byte release payload passes below the audited 377 KiB gate.
- Documentation metadata, policy, worklog, graph, and diff validation pass.

## Follow-ups

Install this exact checkpoint, refresh and visually inspect the authenticated
dashboard, then record that evidence in AR-296. Tracker linkage remains pending
explicit authorization.
