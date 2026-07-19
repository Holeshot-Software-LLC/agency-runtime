---
title: Make configuration the primary source of runtime truth
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [configuration, security, portability]
related:
  - docs/roadmap/issue-AR-53-bind-host-processes-to-install-config.md
  - docs/roadmap/issue-AR-50-fail-closed-runtime-environment-overrides.md
  - docs/roadmap/issue-AR-47-freeze-store-config-identity-at-construction.md
  - docs/roadmap/issue-AR-48-enforce-strict-schema-on-config-read.md
  - docs/roadmap/issue-AR-46-bind-routing-to-store-config-identity.md
  - docs/roadmap/issue-AR-45-bind-store-privacy-to-explicit-config.md
  - docs/roadmap/issue-AR-44-bind-default-store-to-explicit-config.md
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-28-reversible-agent-activation-controls.md
  - docs/roadmap/issue-AR-32-windows-dashboard-task-xml-canonicalization.md
  - docs/roadmap/issue-AR-36-config-relative-runtime-paths.md
  - docs/roadmap/issue-AR-38-dashboard-service-environment-durability.md
  - docs/roadmap/issue-AR-39-fail-closed-storage-config-identity.md
  - docs/roadmap/issue-AR-40-dashboard-config-identity-binding.md
  - docs/roadmap/issue-AR-68-require-trusted-config-and-policy-namespaces.md
  - docs/roadmap/issue-AR-73-require-private-custom-policy-files.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0006
type: decision
deciders: []
---

# ADR-0006: Make configuration the primary source of runtime truth

## Context

The runtime needs reproducible behavior across interactive shells, background hosts, and machines where environment setup differs. Credentials and provider order also need a durable home without leaking through diagnostics or generated documentation.

## Decision

Treat the user configuration file as the primary source for runtime settings, provider entries, and direct credentials. Apply environment variables as explicit higher-precedence deployment overrides, then fall back to bundled defaults.

Resolve direct credential values before environment references. Redact credential fields from normal configuration output, authenticate health checks, normalize YAML booleans consistently, expand user-relative storage paths, and protect the user configuration file with owner-only permissions where the platform supports them.

Before any canonical runtime read, require the configuration file's real parent
namespace to prevent cross-account name substitution. Bind explicit and
environment-selected paths to the same rule used by CLI and dashboard writes,
including capability-safe creation below restricted host scratch.

## Consequences

- A configured runtime behaves consistently when launched outside the shell that created it.
- Direct credentials can support hosts that do not propagate environment variables.
- Diagnostic output must remain redacted by default.
- Configuration migration and validation become part of the compatibility surface.

## Alternatives

- Require environment variables for every credential. Rejected because service and plugin launch contexts often differ from the user's shell.
- Store credentials in the database. Rejected for now because it would complicate configuration inspection and migration without adding a clear security boundary.
- Make bundled defaults authoritative. Rejected because machine-specific provider and storage choices must be explicit.

## Provenance

Commit 3b39f58 established config-first credentials, authenticated doctor checks, redaction, normalized booleans, and resolved user paths. The README documents the effective precedence as environment overrides, user configuration, then bundled defaults.
