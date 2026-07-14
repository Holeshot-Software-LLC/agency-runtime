---
title: Generate one Python hook scaffold for every host
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [installer, adapters, historical]
related: []
supersedes: []
superseded_by: docs/decisions/0024-native-host-packages-and-minimal-bridges.md
id: ADR-0009
type: decision
deciders: []
---

# ADR-0009: Generate one Python hook scaffold for every host

## Context

One-command installation needed a simple way to write integrations for several detected hosts. The first installer assumed a common registration lifecycle and could generate the same Python hook shape with a different adapter import.

## Decision

Generate a Python package entry file for every host. Register preflight, pre-verify, post-tool, post-request, and output-transform hooks through one shared template.

## Consequences

- The initial installer was compact and easy to smoke-import.
- Hosts with a matching Python hook lifecycle could share one template.
- A generated file could exist without being discoverable if the host required a manifest.
- Hosts with a different language, directory, or lifecycle contract received scaffolding rather than a working native integration.

## Alternatives

- Implement each host's native package format from the start. Deferred while the installer and shared runtime were still being proven.
- Ship wrapper commands only. Rejected because hosts with plugin hooks can provide stronger preflight and finalization evidence.
- Detect each host but report unsupported until a native integration exists. Safer, but did not meet the original one-command integration goal.

## Provenance

Commit a7bba3a introduced the uniform generated plugin template. The historical handoff explicitly warned that some generated integrations were scaffolds until their real loading mechanisms were verified. Commit 63b75ee superseded the universal-format assumption.
