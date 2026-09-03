---
title: "Form the retrieval subject before the turn that needs it"
status: proposed
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [routing, retrieval, staffing, workforce]
related:
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
supersedes: []
superseded_by: null
id: ADR-0197
type: decision
deciders: [owner]
---

# ADR-0197: Form the retrieval subject before the turn that needs it

## Status

**Proposed.** AR-370 records owner direction on the shape of the fix but not a
choice between the three costed options. This ADR exists to make that choice
decidable; it should not be marked accepted until the owner picks an option.

## Context

An operational request retrieves nothing usable. Measured 2026-09-03 on the
installed runtime, thirty prompts through `agency route --host codex`:

- `Install ripgrep on this machine` and `configure the gateway` score **0.0
  against every one of the 291 cards**.
- Seven of the thirty score zero across the board. The candidate list then
  degenerates to slug order, which AR-370's partial fix now labels rather than
  presents as a ranking.
- Twenty-three score normally. `Add a typed async Python CLI with packaging and
  failure-path tests` scores `python-application-engineer` 24.0.

Retrieval is healthy. The question is impoverished, exactly as AR-370 measured:
the subject of "install **this**" is a URL, and the words that would match a
card — CLI, tool, linux, package — are never stated and never inferred.

### The tracing corrects two assumptions

**The workforce recall already runs on a typed subject.** `_run_hybrid_recall`
(`core/workforce/inference.py:1937`) takes `plan: WorkUnitPlan`, not the user's
message. The staffing path is not retrieving on raw text.

**Planning does not depend on selector retrieval.** `plan_and_staff_workforce`
(`core/workforce/inference.py:3364`) takes `request: str` and the full
`WorkforceIndexSnapshot`. It never receives the selector's candidate set, so
"plan before retrieving" is a **reordering**, not a dependency inversion. This
is the single most important fact for costing the options below, and it makes
the change materially cheaper than AR-370 assumed.

So the gap is in exactly two places, both upstream of the typed recall:

1. **The planner's input** is the raw message. A request whose subject is a URL
   produces a weak plan, and the typed recall faithfully inherits it.
2. **The selector's query** (`routing_query`, built at
   `core/selector/pipeline.py:486`) is the raw message plus
   `expand_query`, a 78-line hand-curated table of roughly 25 nouns. Subject
   hints from `workforce_subject_hints_from_plan` are appended at
   `pipeline.py:471-486`, but they arrive from the **previous** turn's plan via
   `preflight_recipe.py:140`. A first turn — which is every turn an operator
   notices — never benefits.

### Constraints the owner has already set

- **No keyword table.** `_DOMAIN_EXPANSIONS` ships one operator's vocabulary
  (`openclaw`, `hermes`, `litellm`, `systemd`) to every installation and is
  already product debt. Growing a lexicon is not an option.
- **No user should have to phrase a request in card vocabulary to get staffed.**
- **Inference is why this system exists.** The fix uses it one stage earlier,
  not a lookup.

## Decision

*To be chosen by the owner. This ADR recommends option C.*

### Option A — always plan first, then retrieve

Move planning ahead of selector retrieval unconditionally, derive subject hints
from the fresh plan, and build `routing_query` from them.

- **Cost:** no new inference call. The planner already runs on every staffed
  turn; this only reorders it. One extra selector retrieval per turn.
- **Risk:** every turn pays the reorder, including the twenty-three in thirty
  that already retrieve correctly. Changes the shape of every routing receipt.

### Option B — a classification pass before retrieval

One small inference call before retrieval emitting only typed fields (domains,
languages, frameworks, capability_ids, platforms).

- **Cost:** an inference call on **every** turn, including turns that already
  route well. Latency on the hot path, and a new provider dependency in front
  of retrieval.
- **Risk:** highest steady-state cost of the three, and a second thing that can
  be `workforce_provider_unavailable` before the turn can even start.

### Option C — retrieve twice, only when the first attempt has no signal *(recommended)*

Retrieve on the raw message as today. When that retrieval returns **no signal**,
plan, derive subject hints, and retrieve once more on the typed subject.

- **Cost:** nothing on the twenty-three in thirty that already score. One extra
  plan-then-retrieve on the seven that currently return slug order.
- **The trigger already exists and is exact.** AR-370's partial fix computes
  `retrieval_signal` and `max_score` from the candidate scores
  (`cli/roster_commands.py`). `retrieval_signal == "none"` — every card at 0.0 —
  is a precise, cheap, non-inferential predicate. No threshold to tune, no
  vocabulary to maintain.
- **Risk:** two retrieval shapes to reason about in receipts, and the second
  pass must be bounded so a pathological turn cannot loop.

Option C is AR-370's own proposal, with A as its fallback shape. What is new
here is that the trigger is no longer a judgement call: the zero-signal
predicate landed on 2026-09-03 and is already measured to fire on exactly the
seven prompts that need it and none of the twenty-three that do not.

## Consequences

- A turn that currently returns slug order gets one more plan-and-retrieve and
  a real candidate set, or fails honestly with a receipt showing both attempts.
- Routing receipts gain a second retrieval record. The zero-signal marker stays
  as the trigger and as the honest answer when the second pass also finds
  nothing.
- `_DOMAIN_EXPANSIONS` is not extended. Whether it is *removed* once the typed
  subject carries the load is a separate decision with its own measurement.
- This is a policy surface: the change needs the routing and
  decision-conformance evals, and a mutation-conformance anchor on the trigger
  so it cannot be silently loosened into "retry when confidence is lowish".

## Alternatives

- **Grow the expansion table.** Rejected by standing owner direction: it is
  product debt, it ships one operator's vocabulary, and it cannot generalize.
- **Lower the score floor so something always ranks.** Rejected: it converts an
  honest "no signal" into a confident wrong answer, which is the behaviour
  AR-370's partial fix just removed.
- **Leave it and rely on the operator rephrasing.** Rejected against the stated
  constraint that no user should have to phrase a request in card vocabulary.

## Open question for the owner

Option C pays only on failing turns but leaves two retrieval paths. Option A is
one path for every turn at the cost of reordering all of them. If the reorder
proves cheap in the routing eval — and the tracing above says it should, since
planning never depended on retrieval — A may be worth the uniformity. That
measurement is the natural first task under whichever option is chosen.
