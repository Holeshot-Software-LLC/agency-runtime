---
title: "AR-198: Install the applicable suite by default"
status: done
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [installation, host-integrations, dashboard, discovery, usability]
related:
  - docs/decisions/0111-install-the-applicable-suite-by-default.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/handoffs/issue-AR-198.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-198
priority: p0
tracker_url: null
depends_on: [AR-197]
blocks: []
---

# AR-198: Install the applicable suite by default

## Problem

Installation treated host selection and dashboard installation as loosely
coupled special cases. The shortest command did not clearly mean “install the
applicable product,” and a dashboard preflight failure could prevent harness
integration work from running.

## Current state

ADR-0111 defines the superseding full-suite contract. Implementation, focused
verification, the named fast spine, dashboard UI suite, routing evaluation, and
write-free live dry run are complete. Tracker creation remains pending explicit
authorization; no outward write was made.

## Approach

Make an omitted host selector equivalent to automatic discovery, preserve
`--all` as an explicit compatible spelling, and retain `--agent` as a narrowing
selector. Keep dashboard installation enabled unless `--no-dashboard` is
present. Run and report selected host transactions independently, and keep
dashboard failure from suppressing successful host registration.

## Dependencies

AR-197 removes the Agency-owned Windows Hello helper. ADR-0111 governs default
selection, opt-outs, transaction isolation, and aggregate result semantics.

## Acceptance

- [x] Bare `agency install` discovers every installed supported harness.
- [x] The dashboard is selected by default and `--no-dashboard` excludes it.
- [x] `--agent <host>` narrows host scope and `--all` remains compatible.
- [x] One host failure does not prevent later selected hosts from running.
- [x] Dashboard preflight or installation failure does not block host work.
- [x] JSON reports selected hosts and whether the overall result is partial.
- [x] Focused installer, parser, authority-boundary, packaging, and docs checks
  pass (358 installer/authority tests, 324 packaging tests, docs validation).
- [x] The named fast production spine passes (646 passed, 6 skipped) and the
  dashboard UI suite passes (109 passed).
- [x] A write-free full-suite dry run demonstrates Windows discovery of Codex
  and ZCode plus a ready dashboard plan with `ok=true` and `complete=true`.
- [x] Routing evaluation version 1.3.0 passes every routing, policy,
  delegation, performance, retrieval-scale, and CLI-startup gate.
