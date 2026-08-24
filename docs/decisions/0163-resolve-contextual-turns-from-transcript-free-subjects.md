---
title: "Resolve contextual turns from transcript-free same-session subjects"
status: accepted
category: decisions
created: 2026-08-24
updated: 2026-08-24
tags: [routing, classification, privacy, workforce, correlation]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
  - docs/roadmap/handoffs/issue-AR-265.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0163
type: decision
deciders: [maintainers]
---

# ADR-0163: Resolve contextual turns from transcript-free same-session subjects

## Context

ADR-0064 gives the turn classifier bounded durable lifecycle state, but that
state describes whether work exists rather than what the work concerns. A
fresh workforce inference over a message such as `what's next?` can therefore
decide that expertise is useful while still seeing no subject from which to
choose relevant expertise.

Raw prior user or assistant messages would supply that subject, but they cross
a different privacy and provider-egress boundary. Opting into observability
content capture authorizes bounded local retention for diagnostics; it does
not authorize historical text to become a new live control-plane input or to
be sent to another inference provider.

## Decision

For context-dependent external turns, derive one bounded subject capsule from
the exact prior substantive turn in the same session and host. Completed
acknowledgement, control, social, and parent-only advisory rows may be skipped
through a bounded lookup so they do not hide the governing work.

The capsule may contain only source trace, status, and turn kind; selected
specialist card slugs, bounded descriptions, and capabilities; bounded
workforce unit descriptors; and closed subject identifiers for domains,
languages, frameworks, capability IDs, and platforms. It excludes prior user
and assistant text, request summaries, outcomes, resources, paths, risks,
acceptance prose, and final responses. `capture_content=true` does not widen
this projection. Legacy recipes without typed subject fields degrade to
metadata-only context and never trigger a transcript scan.

Pass the capsule to planner and recruiter inference as a separate explicitly
untrusted JSON field. It may resolve the referent of the current message but is
not an instruction, worker choice, permission, or execution authority.
Historical specialist identities are evidence to rerank against the current
eligible roster, never sticky selections. The current user message remains the
only request and permission surface.

Bind the capsule digest into planner and recruiter cache identities and the
durable routing receipt. Recipe v15 carries a source guard containing the
exact source trace and sequence, evidence revision, recipe digest, context
digest, and roster generation. The ready transaction reselects the same prior
row and revalidates that guard. A changed source or roster fails the commit
rather than publishing a stale contextual route.

Every external turn runs classification and produces a current-turn routing
receipt before its response header is rendered. The header reports that
receipt; printing the header is not itself a routing trigger.

An advisory turn may use inference-owned gap hiring to found a missing
specialist for its assessment. That internal workforce mutation does not widen
the work unit: advisory projection still requires one parent analysis unit,
`advise` authority, `read_only` mutation scope, load delivery, and no native
child, workspace write, or external write.

## Consequences

Short contextual questions can select subject-appropriate expertise without
retransmitting conversation history. Identical messages in different work
contexts have distinct planner inputs and cache identities, and the receipt
states when context was applied and which source trace supplied it.

The Store retains a small new semantic projection in v15 recipes. Its schema,
size, source correlation, purpose, and transaction guard therefore become
security and data-governance contracts. Context races fail safe and may require
the host to retry the external turn.

## Alternatives

Sending the complete session transcript was rejected because it expands
retention, prompt-injection, and provider-egress exposure. Reusing
`runs.user_message` whenever content capture is enabled was rejected because
diagnostic retention is not consent for live reprocessing. Reusing the prior
specialist selection without fresh inference was rejected because historical
workers may be stale, disabled, or wrong for the new question. Leaving the
planner with only the literal short message was rejected because it preserves
generic steward routing instead of resolving the active subject.
