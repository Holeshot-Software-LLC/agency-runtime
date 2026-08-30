---
title: "AR-195: Separate Codex canary parent and child goals"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [codex, canary, activation, delegation, observability]
related:
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/preflight_recipe.py
  - agency_runtime/core/selector/pipeline.py
  - tests/test_activation_canary_contract.py
  - tests/test_codex_activation_canary.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-195
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-180, AR-185]
---

# AR-195: Separate Codex canary parent and child goals

## Problem

The current-profile activation canary uses one parent request both to require
native delegation and as the exact child work-unit goal. That goal tells the
child to delegate the same work again. A parent that correctly translates the
request into a direct child review task no longer matches the persisted goal
hash, so the PreToolUse hook refuses it. The model can then retry the same
blocked topology until the outer canary deadline expires.

The retained activation projection also collapses a proven `codex exec`
timeout into a generic unmet-prerequisites sentence. The canary remains
fail-closed, but operators cannot distinguish a timeout from evidence or
process failure without inspecting private local artifacts.

## Current state

Exact installed revision `10ce6e0` passed hook trust, authoritative master
control, deterministic routing, and one-unit planning. The parent model invoked
`spawn_agent` seven times with the exact native task label, but every call was
denied for persisted-goal mismatch; no child, activation grant, specialist
load, finalization, model receipt, or attestation was recorded. The parent then
entered `wait_agent`, and the 180-second outer deadline contained the process.
The retained rollout encrypts parent task arguments, so it does not prove
whether Codex supplied opaque or nonmatching plaintext to the hook. The fixed
denial and zero child evidence do prove that the current parent/child contract
cannot complete. Tracker creation remains pending explicit authorization.

The source candidate now defines and replays a distinct direct child goal,
retains the general hook equality guard, explicitly forbids spawn/wait retries,
and projects only the fixed `codex_exec_timed_out` reason. One hundred twenty-one
focused canary, hook, proof, and activation tests pass; the strengthened exact
contract module passes 20 tests, and targeted Ruff plus diff checks pass. Exact
installed and live evidence remain pending.

## Approach

Keep exact recognition of the nonce-bound parent probe, but define a separate
canonical direct child review goal. Persist and replay that child goal in the
one-unit activation route. Keep the general PreToolUse goal-hash equality guard
unchanged. Tell the canary parent to stop after the first failed spawn and never
wait for a child that did not start. Project a fixed allowlisted timeout reason
derived only from the owned-process `timed_out` bit; never project raw model,
hook, stdout, stderr, path, or prompt text.

## Dependencies

AR-180 owns the live specialist-activation proof, AR-185 owns exact install
verification, AR-191 owns current Codex V2 lifecycle evidence, and AR-192 owns
the pre-model trust gate. ADR-0077 requires a real trusted-hook/native-child
proof rather than a synthetic or bypassed success.

## Acceptance

- [x] The exact parent probe and direct child work-unit goal are distinct,
  bounded constants with focused contract tests.
- [x] Deterministic routing, replay, and the persisted unit assignment all use
  the direct child goal while exact parent recognition remains nonce-bound.
- [x] The general native-child goal equality guard remains unchanged and the
  canonical child goal passes the exact hook contract.
- [ ] One rejected spawn is not retried and no wait is attempted without an
  accepted child.
- [x] A real `codex exec` timeout projects one fixed safe reason while unknown
  or private failure text remains omitted.
- [x] Focused source tests and targeted static checks pass.
- [ ] The named fast production spine passes, followed by one fresh exact
  installed current-profile canary.
