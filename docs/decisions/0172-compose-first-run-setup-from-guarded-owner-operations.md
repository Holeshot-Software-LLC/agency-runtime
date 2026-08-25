---
title: "Compose first-run setup from guarded owner operations"
status: accepted
category: decisions
created: 2026-08-25
updated: 2026-08-25
tags: [onboarding, install, configuration, dashboard, security]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0172
type: decision
deciders: [maintainers]
---

# ADR-0172: Compose first-run setup from guarded owner operations

## Context

Agency Runtime already separates provider configuration, config validation,
native harness installation, dashboard service lifecycle, diagnostics, and
smoke checks. Those boundaries carry important security and evidence
semantics: provider secrets use hidden input or environment indirection, config
writes are atomic, host lifecycle follows native trust, the dashboard is
authenticated and loopback-only, and smoke is not live host proof.

A first-time user experiences those boundaries as fragmentation. Expanding
`agency configure` to perform every mutation would change a stable provider-only
contract and make it harder to understand which stage failed. Letting the
dashboard install host integrations would also broaden a model-facing HTTP
surface across native trust boundaries before a user has completed setup.

## Decision

Make `agency setup` the canonical first-run journey and implement it as a thin
orchestrator over the existing guarded CLI operations. Keep `agency configure`
as the independently callable provider-chain and starter-roster wizard.

Interactive setup retains an existing config by default or explicitly enters
the existing provider interview, validates before installation, identifies the
supported and detected harnesses, asks for all detected or one explicit host,
asks separately about the optional dashboard, then runs doctor and optional
deterministic smoke. Each stage reports its own outcome and setup stops before
later mutations after a hard failure. A degraded diagnostic remains visibly
distinct from both success and failure.

The dashboard presents the same ordered journey and current posture, links to
its existing configuration/provider controls, and offers copy-only attended CLI
commands for host lifecycle and verification. It does not gain a host-install
mutation endpoint, invoke a shell, grant native trust, or claim smoke as live
host evidence.

Agent-facing setup guidance must drive these public surfaces. It must interview
for security profile, provider kind and model, fallback order, credential
indirection, installed and desired harnesses, dashboard choice, optional dense
recall, and evidence expectations. Secrets may be entered only through hidden
prompts or named environment variables and must never be pasted into command
arguments or reports.

## Consequences

Consumers gain one memorable setup command without losing the smaller commands
needed for automation, repair, or diagnosis. Stage boundaries remain testable,
resumable, and honest. An agent can guide setup without synthesizing YAML or
inventing host-specific installation steps.

The walkthrough intentionally does not make every advanced inference profile a
first-run question. Per-stage and per-harness routing plus learned recall remain
advanced configuration after the primary provider works; the README and
dashboard identify those choices and typed-only recall remains safe by default.

The dashboard cannot complete a host install by itself. That is a deliberate
owner-presence boundary, not a parity defect. Release readiness remains governed
by the release checklist and exact artifact/live evidence rather than by a
successful setup or deterministic smoke run.

## Alternatives

Expanding `agency configure` into an all-purpose installer was rejected because
it would silently broaden a stable command and conflate config, native trust,
service, and evidence failures. Reimplementing those operations in a new wizard
was rejected because duplicate writers drift. A dashboard mutation endpoint
was rejected because initial setup should not expose native host lifecycle to a
model-facing HTTP surface. Documentation alone was rejected because it leaves
users and installation agents to reconstruct ordering and recovery semantics.
