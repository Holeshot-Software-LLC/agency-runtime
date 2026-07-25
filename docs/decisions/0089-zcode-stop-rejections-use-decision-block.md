---
title: "ZCode Stop rejections use decision:block"
status: accepted
category: decisions
created: 2026-07-25
updated: 2026-07-25
tags: [governance, host-integrations, zcode, observability, reliability]
related:
  - AGENTS.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/header/contract.py
  - tests/test_host_hooks.py
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/decisions/0007-six-line-evidence-header.md
supersedes: []
superseded_by: null
id: ADR-0089
type: decision
deciders: [maintainers]
---

# ADR-0089: ZCode Stop rejections use decision:block

## Context

The Agency evidence header is enforced at the native `Stop` hook. The
detection layer (`validate_completion_policy` in
`agency_runtime/core/header/contract.py`) correctly and consistently
classifies a final response as accept-or-reject every turn. The rejection is
then translated to a host-native JSON envelope by
`HookBridge._reject_completion` in `agency_runtime/adapters/hooks.py`.

That translation emits two shapes via `_completion_rejection` (hooks.py:146):

- `retry=True`  -> `{"continue": False, "stopReason": ...}`
- `retry=False` -> `{"decision": "block", "reason": ...}`

The `codex` host is special-cased to force the shared lifecycle shape, but
there was no `zcode` branch, so zcode inherited whichever `retry` value the
caller passed. Which value that is depends on the SQLite continuation state
(the `claim_continuation` outcome): the first rejection on a turn takes the
`claimed` path (`retry=False`, decision:block) while retry-exhausted and
verifier-unavailable paths pass `retry=True` (lifecycle shape).

Per the ZCode hooks contract, `continue` and `stopReason` are unknown fields
that ZCode silently ignores; only `{"decision": "block", ...}` actually stops
the session. A rejection emitted in the lifecycle shape therefore collapsed
into a silent pass-through accept. Because the shape was chosen by retry
state rather than response content, enforcement was intermittent: a missing
header was accepted on some turns and rejected on others, and the behavior
was not under the model's or the runtime's control.

## Decision

`HookBridge._reject_completion` emits `{"decision": "block", "reason": ...}`
for the `zcode` host on **every** rejection path, regardless of the caller's
`retry` state. This mirrors the existing `codex` branch in structure but is
inverted in value, because ZCode and Codex recognize opposite shapes.

The contract is locked by parametrizing the existing blank-stop-response test
over `zcode` and by a dedicated regression test asserting the shape on both
the claimed and exhausted continuation paths.

## Consequences

- ZCode Stop rejections now reliably block. A response missing the Agency
  header can no longer be silently accepted because of retry state.
- ZCode loses the retry-correction affordance that the lifecycle shape
  carries for Codex: a rejected response is blocked rather than fed back to
  the model with a correction reason in the same envelope. This is acceptable
  because ZCode re-injects correction context via its own continuation
  mechanism (the `<!-- agency-continuation:... -->` receipt already attached
  to the reason), and because fail-closed behavior is the governing property.
- The turn-5 "present header reported as missing" symptom observed in the
  originating session is **not** fixed by this decision. It stems from
  `last_assistant_message` reaching the hook as a truncated preview, and
  requires a separate change (full-response delivery or validation against
  the authoritative finalized text). It is tracked as a follow-up in AR-127.

## Alternatives

- **Teach ZCode to recognize the `{"continue": False, "stopReason": ...}`
  lifecycle shape.** Rejected: ZCode's hook contract is outside this
  repository's control, and the lifecycle shape is host-specific anyway.
- **Always emit the lifecycle shape and rely on the continuation receipt.**
  Rejected: it would leave ZCode with no effective block, preserving the
  exact silent pass-through defect this decision removes.
- **Validate against the authoritative finalized text instead of the hook
  payload.** Out of scope here; it addresses the separate turn-5 defect and
  is left to the AR-127 follow-up.
