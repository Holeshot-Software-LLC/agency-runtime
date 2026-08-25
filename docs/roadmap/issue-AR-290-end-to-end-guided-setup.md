---
title: "AR-290: Add end-to-end guided setup"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [onboarding, install, configuration, dashboard, documentation]
related:
  - README.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-112-public-user-readme.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-290
priority: p1
tracker_url: null
depends_on: [AR-05]
blocks: []
---

# AR-290: Add end-to-end guided setup

## Problem

Agency Runtime has safe, tested commands for provider configuration, config
validation, native harness installation, dashboard service installation,
diagnostics, and smoke checks. A consumer must nevertheless discover their
order and translate several separate surfaces into one first-run journey.
`agency configure` is described as guided setup even though it stops after the
provider chain and starter roster; it does not ask which harnesses to wire,
whether to install the dashboard, or whether to run verification.

The dashboard exposes the same configuration writer and provider builder, but
does not present a first-run checklist. The public README contains detailed
architecture and operating commands without one canonical setup path or a safe
prompt a consumer can paste to an installation agent.

## Current state

- `agency configure` safely interviews for security posture, inference
  providers, fallback order, authentication indirection, detected adapters,
  and tuning.
- `agency install` safely auto-detects all five supported harnesses, can scope
  to one harness, and selects the optional user dashboard service by default.
- `agency config validate`, `agency doctor`, and `agency smoke --all` provide
  distinct configuration, diagnostic, and deterministic smoke evidence.
- The dashboard supports authenticated configuration and provider editing, but
  host lifecycle mutation intentionally remains an attended CLI operation.
- The repository is prerelease. AR-119 exact-candidate host evidence, current
  artifact matrices, benchmark outcomes, tracker parity, and publication
  authorization remain release blockers; additional local smoke alone cannot
  close them.
- Tracker creation is pending explicit authorization. No outward tracker write
  is authorized by this local package.

## Approach

Add `agency setup` as a thin owner-interactive orchestrator over the existing
guarded command implementations. It must preserve the provider wizard and
atomic writer, validate the resulting or retained config, ask for all detected
or one explicit harness, ask whether to install the dashboard, run diagnostics,
and offer deterministic smoke verification. Existing config is retained by
default; replacement and every optional mutation remain explicit.

Expose an ordered setup journey in the dashboard Settings view. It may report
configuration and host posture, navigate to the existing provider editor, and
copy attended CLI commands. It must not introduce a dashboard host-install
mutation endpoint or bypass native harness trust.

Rewrite the public entry path in `README.md` around a consumer journey. Include
plain-language product and support summaries, Mermaid architecture/setup
diagrams, current prerelease limits, and a paste-ready agent prompt that asks
the user for provider/model, fallback, harness, dashboard, recall, secret, and
verification decisions before running `agency setup` and the documented
advanced configuration surfaces.

## Dependencies

- AR-05 owns the interactive provider-chain wizard and secret-safe validation.
- Existing installer, dashboard service, doctor, and smoke commands remain the
  authorities for their stages; setup does not duplicate their mutations.
- ADR-0031 keeps the dashboard optional and user-scoped.
- Tracker creation and every push, pull request, hosted workflow, tag, or
  release action require separate authorization.

## Acceptance

- [ ] `agency setup` interviews for retained versus replaced configuration,
      inference provider setup, harness scope, dashboard installation, and
      smoke verification, then prints a stage-by-stage result.
- [ ] Non-interactive setup has explicit bounded flags and never places secret
      values on command lines, in JSON, or in durable evidence.
- [ ] Existing `agency configure`, install, validation, doctor, smoke, native
      trust, and dashboard-service contracts remain authoritative and
      independently callable.
- [ ] The dashboard shows one ordered setup walkthrough with truthful current
      posture and copy-only attended commands; it gains no host mutation API.
- [ ] The consumer README contains a clear quick start, capability/support
      tables, architecture and setup diagrams, current prerelease limits, and a
      paste-ready agent setup prompt.
- [ ] Focused CLI/parser/dashboard tests, the named fast spine, dashboard UI,
      documentation, Ruff, routing, decision conformance, and diff gates pass.
- [ ] Release readiness is reported against the canonical checklist without
      treating local smoke as current artifact, host, tracker, or publication
      proof.
- [ ] Tracker creation and linkage remain pending separate authorization.
