---
title: Provide one-command install and a reversible host toggle
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-11
tags: [installer, operations, usability]
related:
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0010
type: decision
deciders: []
---

# ADR-0010: Provide one-command install and a reversible host toggle

## Context

A portable runtime is not useful if every host requires a bespoke manual installation. Operators also need to disable host wiring without deleting evidence or roster state.

## Decision

Provide three installation modes: detect and install all supported hosts, install one named host, or seed the standalone runtime without host wiring.

Detect hosts through known locations and executable lookup. Install generated native files that import the package. Disable compatible host wiring by renaming the active entry file to a disabled form and re-enable it by reversing that rename. Do not delete SQLite state when toggling.

## Consequences

- Initial setup is scriptable and discoverable.
- A host can be disabled persistently without losing audit or roster data.
- Installation success must mean the host can actually discover and execute the generated integration, not merely that a file was written.
- A file rename affects restart-time loading; immediate in-process toggles may require a separate runtime setting.

## Alternatives

- Require users to copy integration files manually. Rejected because it is error-prone and not portable.
- Uninstall files and delete state when disabling. Rejected because disablement should be reversible.
- Always install every host. Rejected because standalone and least-change use cases need a narrower mode.

## Provenance

Commit a7bba3a introduced host detection, the three installation modes, and rename-based toggles. Commit 63b75ee strengthened installation truth with required manifests and a native package where the common format did not fit.
