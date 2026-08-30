---
title: "Bind Codex canary children by request digest"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, correlation, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_activation_verification.py
  - agency_runtime/core/store/evidence.py
supersedes: []
superseded_by: null
type: worklog
commit: a5c1ad536f13c51ceaa5c1c13d2570b7c166f0a7
short: a5c1ad53
date: 2026-08-27
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
---

# Worklog detail: Bind Codex canary children by request digest

## Purpose

Repair the exact Codex production-container activation canary after fresh host
evidence showed that `SubagentStart` identifies the child session rather than
the already-routed parent session. Preserve ordinary unstaffed behavior and
every existing Store, inference, artifact, and no-bypass boundary.

## Approach

The current-profile exact-canary backend projects the SHA-256 fingerprint of
its unique nonce-bearing task. The child hook requires child
`session_id == agent_id`, resolves a unique Store snapshot by that fingerprint,
and admits only the exact accepted `code-reviewer` route on an active, ready,
unended parent. Parent hooks retain their direct parent-session resolver.

Tests cover malformed and absent capabilities, mismatched child identities,
terminal runs, duplicate routes, ordinary non-exact invocations, and product
rollouts. ADR-0186 records why this bounded digest join is acceptable and why
ambient open-run selection is not.

## Challenges encountered

The preceding fresh Codex transaction completed its child successfully, which
initially made model selection or rollout parsing plausible suspects. The child
rollout instead proved that the hook returned generic identity context, and the
host source confirmed the child-session envelope. A broader optional regression
pass then found three unrelated ledger tests hard-coding schema 46 while the
canonical Store is schema 48; AR-323 records that pre-existing drift without
expanding this repair.

## Decisions and alternatives

[ADR-0186](../decisions/0186-bind-codex-child-session-with-canary-request-digest.md)
owns the security decision. Searching for the sole open run, decrypting opaque
host text, trusting the successful child response, or treating Store presence
as delivery proof were rejected. The digest scopes the join but does not select
a specialist or replace host-authored delivery evidence.

## Verification

- Ruff check and format checks pass for all six changed Python/test files.
- `tests/test_codex_activation_verification.py`,
  `tests/test_canary_activation_snapshot.py`, and
  `tests/test_codex_activation_canary.py` pass 99/99 with `-W error`.
- Nine broader hook/native-child files pass 266 tests; three unrelated stale
  schema-literal assertions fail and are isolated in AR-323.
- Documentation metadata and policy checks passed; documentation parity is
  restored by the immediately following worklog ledger commit.

## Follow-ups

- Rebuild exact artifacts and repeat the fresh no-bypass Codex proof under
  [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md).
- Keep the stale optional ledger assertions bounded to
  [AR-323](../roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md).
- Continue the remaining four-harness, host, dashboard, gate, and teardown work
  under [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md).
