---
title: "Worklog detail: Record installed inference topology"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [dashboard, inference, installation, verification]
related:
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0a5bdb06ad19db7fd4c38467e184b3097dd6490b
short: 0a5bdb06
date: 2026-08-25
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/326
related_issues:
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Record installed inference topology

## Purpose

Close AR-296 with exact installed, authenticated visual, diagnostic, smoke, and
repository-gate evidence instead of treating source tests as installed proof.

## Approach

Bind the local-path install to source with exact dashboard asset hashes, inspect
the effective topology through an authenticated bearer-safe browser session,
and record host lifecycle states separately from deterministic smoke. Preserve
Codex attended trust and cold loading as explicit unknown/degraded states.

## Challenges encountered

The installed consumer CLI intentionally omits development-only `pytest`, so it
could not run the decision-conformance baseline. The required gate was rerun
through the candidate source with the repository development interpreter and
killed all 160 curated mutations without changing source.

## Decisions and alternatives

No host trust or loading claim was inferred from registration, enabled plugin
files, dashboard status, deterministic smoke, or model-facing text. Exact
installed asset hashes were used because a local-path package install does not
publish a VCS source revision in its metadata.

## Verification

- Installed source/asset hashes match and the owned dashboard service is active,
  current, drift-free, and reachable.
- Authenticated visual inspection shows 13 profiles, 11 routes, strict
  assurance, additive recall, Jina roles, thinking levels, judge roles, and the
  native-host execution boundary without rendering secrets.
- Installed status exits 0; doctor exits degraded 2 only for attended/cold-host
  evidence; deterministic smoke passes 8/8.
- The 839-test fast spine, 138 dashboard UI tests, Ruff, documentation, routing,
  and all 160 decision mutations pass.

## Follow-ups

Tracker parity remains pending explicit authorization. Unattended ephemeral
container activation is a distinct production deployment contract and must be
tracked and proven independently from this workstation acceptance.
