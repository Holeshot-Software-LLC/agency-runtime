---
title: "Schedule assurance by artifact lifecycle"
status: accepted
category: decisions
created: 2026-07-21
updated: 2026-07-21
tags: [assurance, delegation, lifecycle, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-124-lifecycle-assurance-and-native-delegation.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
supersedes: []
superseded_by: null
id: ADR-0082
type: decision
deciders: [maintainers]
---

# ADR-0082: Schedule assurance by artifact lifecycle

## Context

Keyword-triggered reviewers can run before an artifact exists, waste context,
and produce unsupported completion claims. Native hosts already own delegation
and should not be replaced by a second execution hierarchy.

## Decision

Planning records assurance requirements and lifecycle timing, but activation
occurs only when the required artifact or evidence transition exists. Reviewers
run independently from implementers, conflicting governing methods use separate
contexts, and production completion requires integration and release evidence.
Agency supplies exact-version activation recipes while Codex, Claude Code,
OpenClaw, and Hermes retain native delegation ownership.

## Consequences

Assurance becomes relevant, independent, and evidence-backed. The runtime must
observe artifact transitions, preserve parent-approved recipes across bridges,
and distinguish assigned, activated, completed, and accepted states.

## Alternatives

Always loading generic reviewers was rejected as noisy and premature. Replacing
native delegation was rejected because it would conflict with host scheduling.
Treating worker completion as application completion was rejected because it
does not prove integration, installation, or release quality.
