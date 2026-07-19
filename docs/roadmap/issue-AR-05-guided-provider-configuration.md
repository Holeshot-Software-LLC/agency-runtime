---
title: "AR-05: Complete guided provider configuration"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-18
tags: [configuration, providers]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0008-ordered-provider-fallback.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-05
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/5"
depends_on: []
blocks: [AR-06, AR-07, AR-80]
---

# AR-05: Complete guided provider configuration

## Problem

The runtime supports an ordered provider fallback chain, but the interactive setup path must let a user construct, validate, and safely persist that chain. Selecting one judge provider does not expose the product's actual fallback model.

## Current state

Interactive setup now starts from detected providers and exposes the real ordered
`providers` chain. The editor can add, move, and remove Ollama, OpenAI,
Anthropic, LiteLLM, custom OpenAI-compatible, Codex CLI, and Claude CLI
entries. Chains are capped at the same four entries the runtime can attempt, so
valid configuration is never silently ignored.

Authentication can use an environment-variable reference, a hidden direct-key
prompt, or no key for an explicitly loopback-compatible endpoint. Discovery
runs only after authentication is selected. Remote catalog responses are
redirect-refusing, byte/count/string bounded, and control-character safe before
any model identifier reaches the terminal.

## Approach

The wizard uses the same typed provider representation and live validation
boundary as `agency doctor`. Each entry is validated in order before an
interactive write, and failures identify `providers.N` plus the provider name
without echoing credentials or remote response bodies. The existing atomic,
owner-restricted configuration writer remains the only persistence path.

A nonempty typed chain is authoritative. Legacy `judge` and separate `ollama`
settings are used only by configurations that have no typed provider chain; a
provider removed in the editor cannot reappear as a hidden or billed fallback.

## Dependencies

None. Its provider representation should remain compatible with the existing config loader and judge fallback loop. It provides the configuration surface needed by `AR-06`.

## Acceptance

- [x] Interactive setup can create and reorder a multi-provider fallback chain.
- [x] Detected, local, and custom OpenAI-compatible providers can be configured without manual YAML editing.
- [x] Direct keys and environment-key references are supported without echoing or logging secrets.
- [x] Every configured provider is validated independently and failures identify the affected entry.
- [x] The resulting file round-trips through config loading, uses restrictive permissions where supported, and passes `agency doctor`.

## Verification

- `tests/test_cli_config_security.py` covers ordered editing, the explicit
  four-entry limit, timeout propagation, local-only bootstrap, authentication
  before discovery, secret-safe output, hostile catalogs, and indexed live
  validation failures.
- `tests/test_configuration.py` covers typed round trips, keyless loopback
  policy, bounded chain size, model-token safety, atomic writes, and restrictive
  permissions.
- `tests/test_doctor.py`, `tests/test_provider_protocols.py`, and
  `tests/test_http_safety.py` cover shared validation, ordered diagnostics,
  protocol-specific checks, and redirect credential isolation.
