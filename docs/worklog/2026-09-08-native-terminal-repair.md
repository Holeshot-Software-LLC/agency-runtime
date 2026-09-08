---
title: "Native terminal repair and four-host verification"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [openclaw, hermes, claude, zcode, finalization]
pr: null
related:
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
---

# Native terminal repair and four-host verification

## Outcome and approach

Starting main and origin match97e269ec, clean. Owned branch
`codex/ar418-ar419-native-terminal-20260908` replaces the merged historical
capsule branch. Observable outcome: an ordinary accepted native turn with exact
headers, injection evidence and central finalization, then Claude/Zcode proof.
Phase: fast_verification; native success remains pending.

The OpenClaw awaited `before_agent_finalize` hook exposes internal delivery as
`ctx.channel=webchat`. A positive pre-verify result now passes its exact text,
session and trace to the existing outbound gate. Other channels still await
complete payload sealing. No staffing, critic, model, token budget or validator
changes. Existing first-invalid policy, native errors and outbound seals remain.

## Evidence and limitations

Twelve executed generated-Node cases cover positive, rejected and unavailable
policy results across webchat, external and missing channels. Focused adapter,
correlation and boundary checks:153passed/one skipped in20.17seconds.
Production spine:1151passed/three skipped in72.28seconds; UI224passed.
Docs1342files, Ruff780files and metadata pass. Routing/conformance are pending. A missing shell Ruff
command is an environment lookup failure, not a lint result; use the existing
private development environment. No exhaustive workflow was dispatched.

Hermes native source has early truncated-result returns outside normal output
transformation and session-end hooks. Both a provider length condition and
malformed tool arguments can produce the same message. The outer runner and
one-shot CLI can report success for printable partial output. No supported
terminal-result hook covers these paths; an adapter-only cleanup change would
not prove repair. The original receipt and unknown provider cause are preserved.

Claude is found on PATH, but inventory rejects its executable parent namespace
permissions. Zcode's configuration hooks are registered/enabled without an
executable, version or proven native capabilities. Both remain in scope.

The current Codex turn is honestly unstaffed: planner, reranker and recruiter
response-contract failures are recorded in its current snapshot. The prior
handoff turn's critic veto is a different receipt and is not reclassified here.
A fresh CLI wiring read reports Codex not_measured; that is not fresh hook proof.

## Next bounded package

Complete fast checks, install the immutable OpenClaw candidate through normal
gateway maintenance, and capture one fresh native result. Preserve all failed
receipts and keep AR-404/418/419 open until isolated criteria have evidence.
