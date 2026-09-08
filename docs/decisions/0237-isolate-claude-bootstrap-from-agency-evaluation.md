---
title: "Isolate Claude bootstrap from Agency evaluation"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [claude, canary, performance, runtime-control]
related:
  - docs/roadmap/issue-AR-410-disable-claude-warmup-staffing.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - agency_runtime/core/canary_backends.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0237
type: decision
deciders: []
---

# ADR-0237: Isolate Claude bootstrap from Agency evaluation

## Context

AR-338 introduced a first print session because a freshly installed Claude
plugin's prompt hooks did not activate until its second session. The warm-up
exists to bootstrap transport, not to satisfy canary evidence. A fresh live
receipt now proves that the one-word warm-up itself enters expensive staffing
and consumes the same deadline as the real evaluation.

## Decision

Keep the installed plugin and its native first session. Add the supported
session-only `--settings '{"disableAllHooks":true}'` only to the fixed warm-up
argv, never plugin staging or the nonce request. Leave master control and its
existing fail-closed projection untouched. Native-only remains unchanged.

Do not change owner state, provider configuration, workforce budgets,
permissions, trust checks or deadlines. A private-control-only solution was
rejected by independent review because generated installed hooks explicitly
bind the owner's control path. The native session setting acts before those
commands are launched. Managed policy can override this setting and must never
be bypassed or rewritten.

The [Claude hook reference](https://code.claude.com/docs/en/hooks#disable-or-remove-hooks)
documents the setting; the [CLI reference](https://code.claude.com/docs/en/cli-usage)
documents inline session settings. Installed CLI 2.1.263 help confirms the
`--settings <file-or-json>` argument. These contracts are not live proof.

This supplements ADR-0036/0158, without replacing their exact nonce routing,
accepted finalization, host-authored artifact, pre-speech card and installation
binding requirements. Warm-up output cannot satisfy any of those requirements.

## Consequences

The transport bootstrap should not launch Agency hooks when the native setting
is honored; managed policy remains an explicit limitation. Native host
model latency remains and may still exhaust the unchanged shared deadline.
The expected improvement is not a measured quality or speed guarantee. A fresh
installed live checkpoint must establish that second-session activation still
works; until then AR-410 remains in_progress.

## Alternatives

- Remove the warm-up: rejected without fresh proof that the host no longer
  needs its first-session initialization.
- Change only an environment diagnostic: rejected because it is not the
  runtime-control authority.
- Disable Agency for the actual request or relax proof: rejected because it
  would change what the canary establishes.
- Raise deadlines or alter the user's staffing profiles: outside this scope.

## Provenance

Source `0e8e9307` and ledger `fb3ef70e` contain the minimal runtime/test change.
