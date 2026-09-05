---
title: "Accept one complete object followed only by closing brackets, and name the repair"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, planner, transport, inference, receipts]
related:
  - docs/roadmap/issue-AR-399-a-plan-object-followed-by-a-stray-brace-reads-as-prose.md
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/decisions/0212-ask-again-when-a-complete-reply-is-not-json.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0215
type: decision
deciders: [owner]
---

# ADR-0215: Accept one complete object followed only by closing brackets, and name the repair

## Status

**Accepted 2026-09-05.** Implements AR-399; refines what "not JSON" means to
the HTTP transport after ADR-0212.

## Context

ADR-0212 gave a complete reply that is not JSON one second ask. Four planner
replies captured live on 2026-09-05 were a complete plan object followed by a
single stray `}`. The transport's parser tried the whole text, then the span
from the first `{` to the last `}`; the stray brace is the last one, so both
attempts failed, the reply was classified `provider_model_text_not_json`, the
second ask drew the same shape, and the turn ended `inference_unavailable`
with a complete plan in hand. Five of the fourteen live receipts after the
`c42fb0a5` install carried exactly this failure.

The same span already accepted trailing prose after a complete object; only a
trailing *bracket* defeated it. Asking the model again is proven not to help.

## Decision

1. When both existing attempts fail, the transport decodes the first complete
   object from the first `{` and accepts it only if everything after it is
   closing brackets, fence ticks or whitespace. The accepted slice is re-read
   through the bounded JSON loader, so the size, depth and node limits still
   hold; a decode that hits the interpreter's recursion limit is refused as not
   JSON rather than raised.
2. The repair is named. `StructuredProviderResult.model_text_repair` carries
   `model_text_trailing_data_trimmed`; the applied attempt records it as a
   validation reason code; the receipt projection admits that runtime-owned
   code for every stage, so a rescued reply is distinguishable from a clean one
   wherever attempts are read.
3. Nothing else widens. A stray bracket followed by other text, or a text with
   no object, is still `provider_model_text_not_json`. No prompt changes.

## Consequences

- The notification-shaped turns that lost their plan now plan on the first
  ask; the second ask of ADR-0212 stays for replies that are not JSON at all.
- A receipt or attempt list shows when a plan needed the repair, so a model
  that starts emitting the brace on every reply is visible, not silently fixed.
- Only the HTTP transport is covered. The CLI transport reads model text with
  the bounded loader directly and gets no repair; the same shape from a codex
  or claude CLI provider still costs the turn. That is recorded as out of
  scope in AR-399, not decided here.

## Rejected alternatives

- **A prompt-side guard.** The request already carries the JSON schema as
  `response_format`; the model emits the brace anyway, and the second ask
  proved that asking again draws the same reply.
- **Trim any trailing text.** The old span already accepts prose after an
  object; widening to arbitrary tails would accept a reply whose object is
  followed by a second, different object, which is exactly the ambiguity the
  bounded loader exists to refuse.
- **Fail the reply and count it.** That is the state this record replaces: a
  complete plan was thrown away twice per turn on ten percent of live turns.
