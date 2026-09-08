---
title: "AR-404 Codex launch repair and native roundtrip"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [codex, credentials, native, verification]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/worklog/2026-09-08-codex-launch-roundtrip.md
supersedes: []
superseded_by: null
---

# AR-404 Codex launch repair and native roundtrip

## Scope and outcome

The owner confirmed native trust and authorized a bounded Codex package:
restore launch connectivity/credentials, prove a fresh native staffed turn with
exact injection and accepted finalization, then measure a small cold/warm sample.
No OpenClaw restart, new credential, changed provider route, weaker staffing or
broad backlog wave is in scope. Main floor is c5516afe; installed runtime remains
4cbebf73. No product code or generated hook changed. Live results are pending.

## Fresh diagnosis, September 8 UTC

At 11:12:06 the installed inspector proved all eight Codex hooks enabled,
exactly once and trusted; missing/modified/untrusted/duplicate/error counts zero.
The previous handoff's untrusted result is now historical.

The current conversation's MCP status returns Transport closed. A separate
fresh process from the actual installed plugin MCP manifest initialized,
listed all eight tools and served agency.status: exit0, no stderr or parse
error. This distinguishes a dead current connection from an unlaunchable server;
it does not reconnect this conversation or prove its finalizer.

All eight LiteLLM profiles reference LITELLM_API_KEY, absent in this process.
The existing owner-private environment file declares that variable beside
native-API and gateway-base variables; its values were not printed or copied.
The Codex wrapper already unsets OPENAI_API_KEY for subscription-login policy,
but never provisioned LiteLLM. Parent ancestry is terminal/bash/node/Codex;
environment inspection stops at the OS permission boundary, not elevated access.

## Owner launch repair

The existing wrapper now provisions the configured LiteLLM variable from the
owner's existing environment file when absent. Function-local bindings prevent
that file's native API key and gateway base from changing the launch policy or
inherited routing override. Existing API-key unset and native exec are preserved;
an inherited LiteLLM key still wins. This is explicit owner launch configuration
under ADR-0204, not a runtime secret-file fallback or global CLI allowlist change.

Wrapper SHA256 changed from
d87f1d17a1dfbc14421d303f173bb9f4cce862490569fc145e24848f5416d276
to f23714086e26ba5b02ecd88522da18fe66372d84cc48a926190133bc49e27673.
Mode remains0755 in an owner-private executable directory. The original wrapper
is retained privately for recovery; no secret file was copied. Agency config and
provider/profile values are unchanged.

## Executed checks

- Bash syntax passes; native version remains codex-cli0.153.4.
- Two metadata-only probes exercised the actual wrapper prefix, replacing only
  final exec with assertions. An absent LiteLLM key becomes present; an inherited
  sentinel remains unchanged. Both preserve the gateway override and remove the
  native API key. No real credential values enter output or evidence.
- Fresh MCP handshake/status passes as above, without a model call.

## Next checkpoint

Run one normal current-profile activation without bypass through the repaired
native launcher. Record staffing, exact card delivery, child execution, header
and finalization separately. Only on success proceed to ordinary MCP-backed
native execution and a small latency sample. No pass or speedup is inferred yet.
