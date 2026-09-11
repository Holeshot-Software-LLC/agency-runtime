---
title: "AR-440: A stale hook runtime blocks every turn without naming itself"
status: open
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [hooks, install, runtime-staleness, claude, reliability]
related:
  - docs/roadmap/evidence/AR-440-stale-hook-proof-20260911.json
  - docs/roadmap/evidence/AR-440-focused-tests-20260911.txt
  - docs/roadmap/evidence/AR-440-fast-spine-20260911.txt
  - docs/roadmap/evidence/AR-440-decision-conformance-20260911.json
  - docs/decisions/0253-name-the-stale-hook-runtime-when-a-turn-cannot-be-verified.md
  - docs/roadmap/issue-AR-436-durable-dashboard-access-without-a-terminal.md
  - docs/decisions/0248-let-the-owner-opt-in-to-a-durable-dashboard-access-token.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-440
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/878
depends_on: []
blocks: []
---

# AR-440: A stale hook runtime blocks every turn without naming itself

## Problem

A Claude session loads the Agency plugin once at start and every hook event
in that session runs the launcher of the digest it loaded; that pin is what
stops a mutable tree from redirecting hook code (see `runtime_staleness`).
The owner's working session began on 2026-09-10 at 18:39Z on plugin
`0.1.0-claude.9c63b87d75cd` (runtime `79138e80…`; every hook command its
transcript records names that projection, and every Stop summary from
2026-09-10T21:35:44Z onward carries the generic reason). Later that evening the
AR-436 rollout wrote `dashboard.durable_access: true` into `agency.yaml`, a
key that runtime's configuration schema does not know. From the next turn
on, every Stop hook in that session raised `ConfigValidationError:
dashboard: contains unsupported fields` while opening the store, the hook
boundary failed closed with the generic message

> Agency Runtime could not verify or persist the turn-scoped evidence
> contract. Do not publish this response; restore the evidence store and
> start a new turn.

and the UserPromptSubmit hook, which fails open by design, recorded no run
for the session: its last run rows are from 2026-09-10 at 21:31Z, all
`preflight_failed`. The plugin's MCP server failed to connect for the same
reason. The stderr line names only the exception class, which the host does
not show. The owner saw the same block on every turn for a day with nothing
that named the cause or the remedy.

The runtime already knows the answer. `runtime_staleness` compares the
running projection with the per-host launcher pointer the last install
wrote, and `_runtime_staleness_notice` reports the drift once, at
SessionStart. A session that was already running when the install happened
never sees that event again, and the boundary-failure path never consults
the comparison.

## Current state

Repaired on branch `claude/ar440-stale-hooks-20260911` per ADR-0253. In
`adapters/hooks.py` a boundary failure reads `runtime_staleness(host)` once;
with drift the Stop rejection names both digest prefixes, the exception
class and the restart (retry shape for claude and codex, block shape for
zcode), and without drift the generic reason is unchanged. The prompt-hook
boundary still publishes and its log entry and the stderr line carry the
same drift. The reason carries digest prefixes, the host name and a
sanitised class name, never the exception message. Regressions cover both
shapes, the no-drift path, the fail-open prompt path with its log fields, a
pointer read that raises, a staleness import that fails (the Stop boundary
still blocks with the generic reason), and the bounded reason. The reason
states the drift beside the failure rather than as its cause: any Stop
boundary failure in a stale session names the drift, and the restart it
recommends is harmless when the two are unrelated. The review of
2026-09-11 corrected the plugin identity above from an earlier guess by
directory time to the projection the transcript names. Filed 2026-09-11 from the
owner's question about the repeated Stop-hook message.

Merged in PR #883 (merge commit `df4e3faf`) and installed on every host at
digest `2e2fb18b6c25` (main `48427d07`). Proof
([evidence](evidence/AR-440-stale-hook-proof-20260911.json)): the projection
this session loaded (`79138e80…`) reports drift against the real pointer
from inside its own process, and the installed hook, meeting a configuration
key it does not know while a scratch pointer names another projection,
rejects the Stop naming both digests, the failure class and the restart. No
newer projection has been installed since, so the third criterion was
restated as that composition; the first real stale session on this
projection will show the reason without a scratch pointer.

## Approach

When a hook's boundary fails and the running runtime differs from the
host's installed pointer, say so where the operator can see it (ADR-0253):
the Stop rejection names both digests, the class of failure and the restart
that fixes it, the prompt-hook log line and the stderr line carry the same
drift, and a boundary failure without drift keeps today's message. The
comparison stays advisory and the boundary stays fail-closed on Stop and
fail-open on UserPromptSubmit; the message content is content-free (digest
prefixes, host name and an exception class name).

## Dependencies

`runtime_staleness` (the per-host pointer and drift report) and the hook
boundary in `adapters/hooks.py`. AR-436 introduced the configuration key
that surfaced the defect; any future key would do the same.

## Acceptance

- [x] A Stop boundary failure while the running runtime differs from the
      installed pointer is rejected with a reason that names both digest
      prefixes, the failure class and the session restart, in the retry shape
      for claude and codex and the block shape for zcode; a boundary failure
      with no drift keeps the existing generic reason.
- [x] A UserPromptSubmit boundary failure still publishes the prompt, and
      its log entry and stderr line name the drift; the focused, named fast
      and decision-conformance checks pass.
- [x] A projection older than the installed one reports the drift from inside
      its own process against the real launcher pointer, and the installed
      hook, given a launcher pointer naming another projection and a
      configuration key it does not know, rejects the Stop with a reason
      naming both digest prefixes and prints the drift on stderr; the first
      real stale session running this projection is expected to show the same
      reason without a scratch pointer.
