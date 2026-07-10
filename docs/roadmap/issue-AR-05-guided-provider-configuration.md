---
title: "AR-05: Complete guided provider configuration"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [configuration, providers]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0008-ordered-provider-fallback.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-05
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/5"
depends_on: []
blocks: [AR-06, AR-07]
---

# AR-05: Complete guided provider configuration

## Problem

The runtime supports an ordered provider fallback chain, but the interactive setup path must let a user construct, validate, and safely persist that chain. Selecting one judge provider does not expose the product's actual fallback model.

## Current state

Non-interactive configuration emits a fixed-order list from detected providers. The interactive wizard discovers models and supports several provider types and custom endpoints, but it selects one legacy judge configuration and does not write an editable `providers` chain. It does not offer fallback reordering or validate every selected provider in sequence before completion.

## Approach

Turn the wizard into an ordered-list editor. Let users add detected or custom providers, choose models, select direct-key or environment-key authentication, reorder fallbacks, and remove entries. Validate each entry independently, show actionable failures without exposing secrets, write restrictive file permissions where the platform supports them, and print exact verification commands.

## Dependencies

None. Its provider representation should remain compatible with the existing config loader and judge fallback loop. It provides the configuration surface needed by `AR-06`.

## Acceptance

- [ ] Interactive setup can create and reorder a multi-provider fallback chain.
- [ ] Detected, local, and custom OpenAI-compatible providers can be configured without manual YAML editing.
- [ ] Direct keys and environment-key references are supported without echoing or logging secrets.
- [ ] Every configured provider is validated independently and failures identify the affected entry.
- [ ] The resulting file round-trips through config loading, uses restrictive permissions where supported, and passes `agency doctor`.
