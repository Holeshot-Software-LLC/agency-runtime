---
title: "AR-298: Expose complete workforce prompts"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [workforce, prompts, cli, dashboard, observability]
related:
  - README.md
  - CHANGELOG.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - agency_runtime/core/store/workforce.py
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-render.js
  - tests/test_workforce_cli.py
  - tests/test_dashboard.py
  - tests/dashboard_ui.test.mjs
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-298
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-298: Expose complete workforce prompts

## Problem

The dashboard exposes only an 8,192-character active-roster prompt preview,
and the CLI workforce detail surface exposes no prompt. Suspended, retired,
merged, and disabled workers therefore lose prompt visibility even though
their immutable versions remain in Agency's Store. Operators also cannot
request an exact historical workforce version. This falls short of the
maximum-visibility requirement for both packaged specialists and dynamically
hired or amended workers.

## Current state

- Immutable prompt content and hashes live in `agent_versions`, while
  `agent_version_lineage` binds each version to a durable workforce identity.
- Active-roster readers correctly enforce routing eligibility, but they are the
  wrong authority for lifecycle-wide operator inspection.
- A stored definition is not proof that a host delivered it to a child; only a
  correlated host artifact can establish delivery.
- Tracker creation remains pending explicit tracker authorization.

## Approach

Add one workforce-scoped Store reader that resolves a worker by stable ID or
slug, selects its current version or an exact immutable lineage version,
validates the stored content identity, and returns bounded full content with
worker, source, relation, version, hash, standing, and truncation provenance.
It must work for active, disabled, suspended, retired, and merged workers.

Expose that reader through the explicit
`agency workforce prompt <worker> [--version ...] [--max-chars ...]` command.
Do not add prompt bodies to list or ordinary status output. Replace the
dashboard preview with the complete bounded definition on the authenticated
owner worker-detail view. Label both surfaces as stored-definition authority
and explicitly state that runtime delivery is not asserted.

## Dependencies

- AR-119 owns durable workforce identities, hiring, amendments, and lineage.
- ADR-0156 owns the separate host-delivery evidence boundary.
- The existing authenticated loopback dashboard boundary owns browser access.

## Acceptance

- [x] Current and exact historical prompt versions resolve only through the
      selected worker's immutable lineage.
- [x] Prompt bodies remain visible for disabled and terminal workforce
      standings.
- [x] Hash/content mismatch and invalid limits fail closed.
- [x] The CLI exposes full bounded content and provenance only through an
      explicit prompt command, with JSON and human output.
- [x] The authenticated dashboard worker detail renders the complete bounded
      definition with source, relation, current/historical state, and hash.
- [x] CLI and dashboard copy state that stored content is not runtime-delivery
      proof.
- [x] Focused Store/CLI/backend/UI tests pass, including retired-worker access.
- [ ] The exact installed dashboard is visually verified without leaking a
      bearer, provider credential, or prompt outside the owner detail view.
- [ ] Tracker creation and linkage receive separate authorization.

## Verification evidence

Source tests exercise an Agency-hired contractor, its current immutable
version, an explicit version request after retirement, bounded truncation, and
human/JSON rendering. The dashboard backend returns the same governed body and
provenance for active and retired workers, and the complete dashboard UI suite
renders the full prompt while keeping the stored-definition/delivery-proof
distinction visible. Together with AR-297's managed-policy projection, the exact
dashboard is 386,366 bytes under an audited 378 KiB ceiling with 706 bytes of
headroom.
