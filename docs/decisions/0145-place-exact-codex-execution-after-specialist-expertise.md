---
title: "Place exact Codex execution after specialist expertise"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, execution, prompts, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - agency_runtime/core/native_child_prompt_delivery.py
  - agency_runtime/adapters/hooks.py
  - tests/test_claude_native_child_hooks.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0145
type: decision
deciders: [maintainers]
---

# ADR-0145: Place exact Codex execution after specialist expertise

## Context

The current Codex direct-child control received its encrypted assignment, used
`apply_patch`, and wrote exact bytes in the inherited workspace. The consumed
Agency writer trial used the same transport and workspace capability, selected
and loaded `minimal-change-engineer`, but produced no tool call or file.

The v3 Agency child envelope placed the exact work-unit execution instruction
before the immutable specialist prompt. That specialist prompt ended with
generic requirements for root-cause evidence, tests, and refusal of arbitrary
text edits. For a deliberately proof-only named-file assignment, those newest
generic instructions conflicted with the already accepted exact action.

## Decision

1. The Codex direct-child envelope is version 4. It delivers the exact audited
   specialist prompt as immutable expertise, followed by the exact current
   work-unit execution contract as the newest instruction.
2. The specialist prompt keeps its independent content hash. Parsing extracts
   only that prompt body and verifies it against the persisted prompt identity.
3. The execution suffix is fixed product text and must be present byte-for-byte
   at the end of the envelope. Missing, moved, or modified suffixes fail closed.
4. The suffix may resolve a generic specialist preference only for the exact
   already accepted assignment. It does not select a specialist, broaden
   mutation authority, weaken hook enforcement, or manufacture completion.
5. A `workspace_write` assignment continues to require a successful local
   `apply_patch` receipt before the child may report success.

## Consequences

- Inference and the immutable specialist identity remain authoritative.
- A specialist's general operating guidance can no longer accidentally turn a
  valid exact proof unit into a readiness response after Agency accepted it.
- Tampering with either the specialist body or execution suffix invalidates the
  delivery, while successful execution still requires real tool and lifecycle
  evidence.

## Alternatives

- **Modify the roster specialist prompt for the sentinel.** Rejected because a
  product proof must not special-case or weaken reusable specialist expertise.
- **Put execution instructions only before the prompt.** Rejected by the
  observed control/product difference and the v3 instruction ordering.
- **Treat child completion as execution.** Rejected because completion without
  the required patch receipt is not workspace-write proof.
