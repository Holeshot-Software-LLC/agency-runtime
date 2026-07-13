---
title: Decision registry
status: active
category: decisions
created: 2026-07-10
updated: 2026-07-12
tags: [architecture, adr, governance]
related:
  - docs/roadmap/README.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Decision registry

This is the single canonical registry for durable architectural, product, and operational decisions in Agency Runtime. All records share one sequence. A decision is not renumbered when its scope or weight changes.

Status meanings:

- **Proposed**: under active consideration.
- **Accepted**: governs the current system.
- **Superseded**: replaced by a newer decision; follow the recorded link.
- **Deprecated**: still present but discouraged and scheduled for removal.
- **Rejected**: considered and deliberately not adopted.

## Superseding chains

- ADR-0002 Resolve Models from Post-Request Logs → ADR-0003 Treat Response Telemetry as Model Truth
- ADR-0004 Cut Over Through a Host-Specific Compatibility Shim → ADR-0005 Keep a Portable Core with Thin Host Adapters
- ADR-0009 Generate One Python Hook Scaffold for Every Host → ADR-0024 Package Each Host Integration in Its Native Format
- ADR-0020 Keep a Partial Companion Policy in Code → ADR-0021 Load a Full Companion Policy with Explicit Precedence
- ADR-0022 Omit Preflight Context for Trivial Messages → ADR-0023 Load Default Companions Even for Trivial Messages

## Architecture and integrations

| ID | Decision | Status |
|---|---|---|
| [ADR-0004](0004-host-specific-compatibility-shim.md) | Cut over through a host-specific compatibility shim | Superseded |
| [ADR-0005](0005-portable-core-thin-host-adapters.md) | Keep a portable core with thin host adapters | Accepted |
| [ADR-0009](0009-uniform-generated-python-hooks.md) | Generate one Python hook scaffold for every host | Superseded |
| [ADR-0010](0010-one-command-install-and-reversible-toggle.md) | Provide one-command install and a reversible host toggle | Accepted |
| [ADR-0024](0024-native-host-packages-and-minimal-bridges.md) | Package each host integration in its native format | Accepted |
| [ADR-0028](0028-host-support-maturity-and-reversible-install.md) | Separate host contract coverage from live support maturity | Accepted |

## Routing, policy, and providers

| ID | Decision | Status |
|---|---|---|
| [ADR-0001](0001-layered-specialist-routing.md) | Use a layered specialist-routing pipeline | Accepted |
| [ADR-0006](0006-config-first-redacted-configuration.md) | Make configuration the primary source of runtime truth | Accepted |
| [ADR-0008](0008-ordered-provider-fallback.md) | Use ordered provider fallback ending in deterministic scoring | Accepted |
| [ADR-0020](0020-partial-companion-policy-in-code.md) | Keep a partial companion policy in code | Superseded |
| [ADR-0021](0021-full-companion-policy-with-precedence.md) | Load a full companion policy with explicit precedence | Accepted |
| [ADR-0022](0022-omit-preflight-for-trivial-messages.md) | Omit preflight context for trivial messages | Superseded |
| [ADR-0023](0023-default-companions-for-trivial-messages.md) | Load default companions even for trivial messages | Accepted |
| [ADR-0030](0030-versioned-quantitative-evaluation-gates.md) | Gate routing changes with versioned quantitative evaluation | Accepted |
| [ADR-0033](0033-explicit-companion-route-availability.md) | Classify every companion route against explicit availability | Accepted |
| [ADR-0035](0035-authoritative-bounded-provider-chain.md) | Use an authoritative bounded provider chain with allowlisted CLI transports | Accepted |

## Evidence and observability

| ID | Decision | Status |
|---|---|---|
| [ADR-0002](0002-model-attribution-from-post-request-logs.md) | Resolve models from post-request logs | Superseded |
| [ADR-0003](0003-response-telemetry-is-model-truth.md) | Treat response telemetry as model truth | Accepted |
| [ADR-0007](0007-six-line-evidence-header.md) | Enforce a six-line response evidence header | Accepted |
| [ADR-0011](0011-explicit-delegation-evidence-lifecycle.md) | Model delegation as an explicit evidence lifecycle | Accepted |
| [ADR-0015](0015-versioned-selection-explain-receipts.md) | Publish versioned selection-explain receipts | Accepted |
| [ADR-0016](0016-central-finalization-and-session-correlation.md) | Centralize finalization and correlate evidence by session | Accepted |
| [ADR-0027](0027-authoritative-runtime-evidence-traces.md) | Derive runtime claims from authoritative correlated evidence | Accepted |

## State and roster governance

| ID | Decision | Status |
|---|---|---|
| [ADR-0012](0012-canonical-sqlite-audit-store.md) | Use SQLite as the canonical audit store with explicit retention | Accepted |
| [ADR-0013](0013-approval-gated-roster-activation.md) | Gate roster activation through quarantine and approval | Accepted |

## Operations and engineering

| ID | Decision | Status |
|---|---|---|
| [ADR-0014](0014-generated-analysis-indexes-stay-local.md) | Keep generated analysis indexes out of version control | Accepted |
| [ADR-0017](0017-sanitized-server-error-boundary.md) | Sanitize errors at the server boundary | Accepted |
| [ADR-0018](0018-signature-aware-delegation-compatibility.md) | Adapt delegate signatures without masking execution errors | Accepted |
| [ADR-0019](0019-bounded-machine-readable-cli-delegation.md) | Make CLI delegation bounded and machine-readable | Accepted |
| [ADR-0026](0026-explicit-test-home-boundaries.md) | Require explicit home boundaries for generated-plugin tests | Accepted |
| [ADR-0029](0029-secure-local-dashboard-and-bounded-observability.md) | Keep the operations dashboard local and observability bounded | Accepted |
| [ADR-0031](0031-optional-user-dashboard-service-and-shared-configuration.md) | Use an optional user-scoped dashboard service with one typed configuration boundary | Accepted |
| [ADR-0032](0032-adaptive-authenticated-dashboard-polling.md) | Use adaptive authenticated polling and source-owned signal visualizations | Accepted |
| [ADR-0034](0034-persistent-soft-host-control.md) | Separate immediate host control from native plugin lifecycle | Accepted |
| [ADR-0036](0036-capability-bound-host-canary-attestations.md) | Bind live host canary attestations to capability and installation identity | Accepted |
| [ADR-0037](0037-layered-pinned-supply-chain-gates.md) | Use layered pinned supply-chain gates | Accepted |
| [ADR-0038](0038-refuse-executable-git-configuration-during-delegation.md) | Refuse executable Git configuration during delegated mutations | Accepted |
| [ADR-0039](0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md) | Fail before DACL mutation under restricted Windows tokens | Accepted |
| [ADR-0040](0040-preserve-environment-owned-python-launchers.md) | Preserve environment-owned Python launchers | Accepted |

## Documentation governance

| ID | Decision | Status |
|---|---|---|
| [ADR-0025](0025-self-contained-linked-documentation.md) | Keep a self-contained planning-to-evidence documentation chain | Accepted |

## Maintenance rules

- Record the decision before or with the implementation that depends on it.
- Update this registry in the same change as a new decision record.
- Never edit an accepted record to hide a changed decision. Add a new record and wire supersedes and superseded_by in both directions.
- Keep decision links repository-local. External systems may be cited as evidence only when the repository does not depend on them for understanding the decision.
