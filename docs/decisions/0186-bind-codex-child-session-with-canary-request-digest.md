---
title: "Bind Codex child sessions with a canary request digest"
status: superseded
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, native-child, correlation, security]
related:
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_activation_verification.py
  - agency_runtime/core/store/evidence.py
  - tests/test_canary_activation_snapshot.py
  - tests/test_codex_activation_verification.py
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
id: ADR-0186
type: decision
deciders: [maintainers]
---

# ADR-0186: Bind Codex child sessions with a canary request digest

## Context

ADR-0179 assumed a Codex child lifecycle hook carried the parent session plus
the host-created child UUID. Fresh `0.149.1` evidence and the corresponding
official source show a different boundary: `SubagentStart` is constructed from
the child's session, so both `session_id` and `agent_id` identify the child.
Agency consequently queried the parent Store with a child UUID and returned
only identity context even though the exact parent route had been accepted.

Selecting an arbitrary open run would make concurrent or stale canaries
ambiguous. Decrypting the host's opaque inter-agent assignment is unavailable
and would widen the trust boundary. The parent invocation already owns one
unique nonce-bearing task whose SHA-256 digest is also the Store's request
fingerprint and accepted route query hash.

## Decision

For the exact current-profile Codex activation canary only, the backend places
the SHA-256 digest of its complete nonce-bearing task in the child process
environment. It does so only when existing-Store enforcement, exact rollout
validation, and the canary rollout contract are all active. Ordinary and
product executions receive no digest capability.

At `SubagentStart` and `SubagentStop`, Agency requires the validated child
`session_id` to equal the validated `agent_id`. It accepts only a lowercase
SHA-256 digest from the restricted environment and resolves the Store snapshot
without a caller-supplied parent session. Resolution must yield exactly one
route and one run, and the snapshot must be proven, resolved, Codex-owned, and
bound to that digest. The route must be the accepted inference-owned
`code-reviewer` activation route with the exact fixed work-unit summary. The
run and route session/trace must agree; the run must be ready, active or
evidence-only, request-fingerprint matched, unended, and unfinalized.

Any missing, malformed, mismatched, duplicated, terminal, or inconsistent
state returns the existing unstaffed identity behavior. The digest identifies
an invocation; it never selects a specialist, supplies a work unit, proves
delivery, or replaces the host artifact and one-use receipt. Parent
`UserPromptSubmit` hooks continue to use the parent session and turn that the
host supplies directly.

## Consequences

The restricted hook can bind a real Codex child UUID to its unique accepted
parent without prompt recovery, opaque-text decryption, global open-run
selection, or a trust bypass. Concurrent nonce-distinct canaries resolve
independently, while replaying the same digest into two persisted routes makes
the snapshot ambiguous and fails closed.

This is deliberately version-shaped. A future Codex lifecycle envelope that
stops equating child `session_id` and `agent_id` will lose staffing until the
host contract is reviewed. Fresh artifact, Store, header, finalization, and
attestation evidence remains mandatory before Installed or Live claims.

## Alternatives

Choosing the sole open Codex run was rejected because concurrency and stale
state make it ambient authority. Using the child UUID to search all parent
records was rejected because no authenticated parent-child edge exists before
staffing. Reading or decrypting the inter-agent assignment was rejected because
the supported hook does not expose it. Reusing the parent session assumption
was rejected by the exact host source and live rollout. Treating a successful
child response or Store route as delivery proof was rejected by ADR-0156 and
ADR-0179.
