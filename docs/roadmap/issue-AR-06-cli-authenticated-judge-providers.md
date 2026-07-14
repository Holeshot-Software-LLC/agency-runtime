---
title: "AR-06: Implement CLI-authenticated judge providers"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-12
tags: [providers, authentication]
related:
  - docs/decisions/0008-ordered-provider-fallback.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-06
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/6"
depends_on: [AR-05]
blocks: [AR-07]
---

# AR-06: Implement CLI-authenticated judge providers

## Problem

Users who already authenticate through a supported local model CLI cannot currently use that authenticated session as a routing judge. Requiring a separate API key adds setup friction and makes the documented `cli` provider type misleading.

## Current state

`type: cli` is now a real, allowlisted provider contract for `transport:
codex` and `transport: claude`. Detection reports executable discovery,
authentication, and usable structured-output capability as separate facts.
Codex is capability-probed for the required non-interactive controls; Claude
must be at least 2.1.205 for the required fail-closed structured-output
behavior.

Both transports accept the routing prompt only on standard input, run in an
empty temporary working directory with isolated home and temp roots, disable
tools and project customizations through their supported controls, and receive
only a narrow platform/proxy/certificate-path environment. Output is drained
concurrently into bounded memory, overflow is discarded, and timeouts terminate
the owned process tree.

## Approach

CLI results normalize into the same selected-ID and confidence contract as HTTP
providers. Missing authentication, unavailable capability, timeout, truncated
output, process failure, and malformed or incomplete structured output are
failures; the selector proceeds in configured order and ultimately uses
deterministic token routing.

Windows executable preparation never passes user-controlled arguments through
a `.cmd` or `.bat` shim. A trusted sibling native executable is preferred, a
sibling PowerShell shim receives discrete literal arguments, and a batch-only
installation is rejected. This shared boundary also protects Codex, Claude,
Hermes, OpenClaw, and generic delegation backends.

## Dependencies

Depends on `AR-05` so CLI-authenticated entries can be configured and validated without hand-editing YAML.

## Acceptance

- [x] At least one supported CLI-authenticated provider completes an authorized live judge selection without an API key.
- [x] Provider detection distinguishes an installed binary from a usable authenticated session.
- [x] Invocation is non-interactive, time-bounded, output-bounded, and secret-safe.
- [x] Failures fall through to the next configured provider and ultimately to deterministic token routing.
- [x] Unit and integration tests cover success, missing authentication, timeout, invalid JSON, and fallback order.

## Verification

- `tests/test_cli_judge_providers.py` covers Codex and Claude capability status,
  keyless success, standard-input prompts, isolated environments, tool gates,
  missing auth, launch failure, timeout, truncation, invalid output, Windows
  model-token safety, and ordered fallback.
- `tests/test_delegation_backends.py` exercises high-volume stdout and stderr,
  owned-process timeouts, successful parents with lingering descendants,
  partial I/O-worker startup, task/environment redaction, batch-only rejection,
  and real `.cmd` plus sibling `.ps1` literal-argument handling across all
  intended host backends.
- On 2026-07-12, the installed Codex 0.144.1 CLI completed an authorized live
  keyless judge selection for a production-safe OAuth architecture task. The
  normalized result was `applied` through `codex-cli (cli:codex)`, selected
  `senior-developer`, `workflow-architect`, and `code-reviewer`, reported
  confidence `0.87`, and completed in `6880 ms`. It reused the current Codex
  authentication session; no Agency Runtime API key was configured or supplied.
- `tests/test_native_installer.py` proves CLI provider timeouts contribute to
  generated host-hook deadlines.
- Deterministic transport and selector coverage plus the dated live keyless
  result satisfy this item's acceptance criteria. Host hook/header canary proof
  is tracked separately by AR-03, AR-04, and AR-17.
