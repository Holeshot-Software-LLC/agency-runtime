---
title: Keep a partial companion policy in code
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [routing, policy, historical]
related: []
supersedes: []
superseded_by: docs/decisions/0021-full-companion-policy-with-precedence.md
id: ADR-0020
type: decision
deciders: []
---

# ADR-0020: Keep a partial companion policy in code

## Context

The first deterministic companion layer needed a small set of action-to-specialist defaults that worked without an external policy file.

## Decision

Embed a small dictionary of broad actions and default specialist identifiers directly in the selector policy module. Use it whenever no configured policy is available.

## Consequences

- The runtime shipped with deterministic defaults and no extra data file.
- Policy changes required source edits.
- The partial action set did not represent the full operating policy.
- Code and external policy behavior could diverge.

## Alternatives

- Require an external policy file. Rejected initially because a missing file should not disable deterministic routing.
- Bundle a complete data file with explicit override precedence. Adopted by ADR-0021.
- Generate policy from the active roster. Rejected because roster membership does not define which specialists are required for an action.

## Provenance

The partial in-code policy predates the visible commit history. Commit 31443bc records its replacement as a four-action hardcoded dictionary and supplies the before-and-after implementation evidence.
