---
title: Use ordered provider fallback ending in deterministic scoring
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-18
tags: [providers, routing, resilience]
related:
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-06-cli-authenticated-judge-providers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0067-require-configured-inference-for-selection.md
id: ADR-0008
type: decision
deciders: []
---

# ADR-0008: Use ordered provider fallback ending in deterministic scoring

## Context

Specialist routing cannot require a particular proxy, vendor, local daemon, or credential style. Provider outages should reduce semantic quality rather than disable routing.

## Decision

Represent judge providers as an ordered configuration list. Try each available provider in order and accept the first successful judgment. Support proxy, direct API, local, and custom compatible endpoints through a shared provider entry contract.

After the configured list, retain legacy judge and local fallback settings for backward compatibility. If every model-backed option fails, return deterministic token-ranked candidates.

## Consequences

- Provider preference is explicit and portable.
- The runtime remains useful with no model service.
- Doctor and configure must report availability and authentication per provider.
- Fallback attempts and the resolved model need receipt evidence so degraded behavior is visible.

## Alternatives

- Require one proxy for all routing. Rejected because portability includes systems without that proxy.
- Select a provider implicitly from whichever credential is present. Rejected because priority would be surprising and hard to reproduce.
- Fail the request when all model providers fail. Rejected because deterministic routing is safer than silent loss of specialist guidance.

## Provenance

Commit dc0be8d introduced the provider-entry model and ordered fallback chain. Commit 3b39f58 established config-first authentication. The historical handoff records provider independence and deterministic token fallback as final-state requirements.
