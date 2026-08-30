---
title: Load a full companion policy with explicit precedence
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-19
tags: [routing, policy, configuration]
related:
  - docs/roadmap/issue-AR-49-key-policy-cache-by-path-identity.md
  - docs/roadmap/issue-AR-02-specialist-coverage-gaps.md
  - docs/roadmap/issue-AR-26-bundle-default-coordinators.md
  - docs/roadmap/issue-AR-68-require-trusted-config-and-policy-namespaces.md
  - docs/roadmap/issue-AR-73-require-private-custom-policy-files.md
  - docs/roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0020-partial-companion-policy-in-code.md]
superseded_by: null
id: ADR-0021
type: decision
deciders: []
---

# ADR-0021: Load a full companion policy with explicit precedence

## Context

The deterministic routing layer grew beyond a few hardcoded actions. Operators need to override it, the package needs complete defaults, and selected companion identifiers must exist in the active roster.

## Decision

Store the complete broad-action companion policy as bundled package data. Resolve policy in this order: an explicit environment path, the user configuration path, then the bundled policy.

Treat every selected policy path as executable routing configuration: its real
parent chain must prevent cross-account mutation before bounded parsing, and
the file identity must remain stable across the read.

Validate and inspect the policy through a CLI surface. Expose matched actions and companion identifiers in route output. Before merging companion selections into a routing result, filter them against the active roster and report unavailable policy entries through validation rather than selecting nonexistent specialists.

## Consequences

- Policy changes are reviewable as data and do not require selector code edits.
- Deployments can override policy without modifying the installed package.
- Bundled defaults keep deterministic routing available on a fresh install.
- Policy coverage and roster coverage become separate, testable concerns.

## Alternatives

- Keep the partial dictionary from ADR-0020. Rejected because it did not cover the operating action matrix.
- Silently select every policy identifier. Rejected because missing roster entries would create false evidence.
- Generate policy solely from roster metadata. Rejected because deterministic companion requirements express governance, not just capability descriptions.

## Provenance

Commit 31443bc replaced the partial in-code dictionary with the bundled full policy, added precedence and active-roster filtering, exposed policy validation, and surfaced companion actions in route output. Commit 3b24614 had already established bundled defaults as a resilient fallback.
