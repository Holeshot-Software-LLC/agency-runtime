---
title: "Build every subprocess environment from least privilege"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-28
tags: [security, processes, credentials, path, installer]
related:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/THREAT_MODEL.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
supersedes: []
superseded_by: null
id: ADR-0091
type: decision
deciders: [maintainers]
---

# ADR-0091: Build every subprocess environment from least privilege

## Context

Freezing `argv[0]` and avoiding a shell secures the initial executable, but the
child environment remains an authority channel. A third-party host CLI does not
need every unrelated provider or developer credential held by the installer.
A delegated backend with an unsafe PATH can resolve repository-controlled
descendant programs after its validated launcher begins.

## Decision

Every subprocess environment starts from an explicit cross-platform allowlist.
The caller adds only variables required by the selected integration and exact
operation. PATH is rebuilt from absolute, existing, non-repository directories
and excludes empty, dot, relative, target-repository, and caller-injected
entries. Explicit unsafe overrides fail before process creation.

Environment construction is centralized and testable. Diagnostic output may
name missing variable keys but never values.

## Consequences

- Ambient credentials no longer leak across integration boundaries.
- Descendant tool lookup receives the same trust discipline as initial
  executable discovery.
- New hosts must declare their required environment keys explicitly.
- Some user customizations that relied on implicit variables must move to
  documented host-specific configuration.

## Alternatives

- **Copy the parent environment and delete known secrets.** Rejected because
  denylisting cannot anticipate unrelated credentials.
- **Sanitize only PATH.** Rejected because it leaves credential inheritance.
- **Clear every variable.** Rejected because platform, locale, proxy, home, and
  selected integration behavior require a small explicit set.
