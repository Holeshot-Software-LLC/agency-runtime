---
title: "Form the retrieval subject before the turn that needs it"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [routing, retrieval, staffing, workforce]
related:
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
supersedes: []
superseded_by: null
id: ADR-0197
type: decision
deciders: [owner]
---

# ADR-0197: Form the retrieval subject before the turn that needs it

## Status

**Accepted 2026-09-03.** The owner first chose option C; the amendment below
showed C cannot reach the filed defect, and the owner then confirmed the revised
recommendation: **option B, gated on the zero-signal trigger**. That is what is
implemented.

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

**Option B, gated on the zero-signal trigger.** A short typed classification
call runs immediately before the planner, and only when lexical narrowing
scored nothing for the message. The options below are retained as the costing
that produced that choice; the amendment after them records why C, the option
first chosen, could not reach the defect.

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

## Amendment (2026-09-03, before implementation)

The owner chose option C. Tracing it to an implementation point showed the
recommendation was made against an incomplete map, and **option C is a no-op
for the failure this issue was filed about**. Recording that before writing
code rather than after.

### `routing_query` never reaches staffing

The query this ADR proposed to rebuild has exactly three consumers, confirmed
by reading every `request.routing_query` reference in
`core/selector/pipeline.py`:

| line | consumer | on the staffing path? |
|---|---|---|
| 1266 | `session_put` — stickiness cache | no |
| 1820 | `session_check` — stickiness reuse | no |
| 1946 | `_semantic_catalog` → `query_judge` | only when `workforce_snapshot is None` |

`plan_and_staff_workforce` is called with `request.user_message`, never with
`routing_query`. On a workforce-enabled install — the normal case — the
workforce branch returns before line 1946, so `routing_query` affects session
stickiness alone.

### The measured scores are a different scorer

The 30-prompt smoke and this issue's own table both measure `pre_narrow`
(`core/selector/candidate_narrow.py:433`), the lexical scorer behind CLI
`route` and `search`, MCP `agency_search_agents`, the HTTP surface, the
dashboard and `explain`. Re-running this issue's table against it reproduces
its winners exactly: `install this: <url>` scores nothing, `install the zcode
CLI on linux from this url` and `set up and install developer tooling on linux`
both put `developer-tooling-engineer` first, and `configure the gateway`
retrieves zero. Different normalization, same ranking.

`pre_narrow` is a browse and diagnostic surface. It is not what staffs a turn.

### Why C therefore does nothing here

Option C is "when the first retrieval has no signal, plan and retrieve again on
the typed subject". On the staffing path there is no second query to form: the
planner **is** what produces the typed subject, it already runs on the raw
message, and `_run_hybrid_recall` already retrieves on the plan it returns.
Re-running retrieval after planning would re-run a query staffing does not
read.

Option A collapses for the same reason. Of the three, only **option B** — a
short typed classification pass *before* the planner — changes what the planner
sees, which is the only input that can improve a plan derived from
`install this: <url>`.

### Revised recommendation

Re-decide between:

- **B, scoped to the planner's input.** One small typed classification call
  ahead of `plan_and_staff_workforce`, not ahead of retrieval. Cost is an
  inference call per staffed turn; it is the only option that reaches the
  filed defect.
- **B gated on the same zero-signal trigger.** Run the classification pass only
  when `pre_narrow` over the eligible catalog returns no signal for the
  message. This keeps C's "pay nothing on turns that already work" property
  while targeting the stage that matters. Measured on this box, that trigger
  fires on 7 of 30 prompts.
- **Split the issue.** The browse surfaces (`pre_narrow`) and the staffing
  planner are two defects with one symptom. AR-370's narrative is the staffing
  one; its measurements are the browse one.

The second is the closest honest descendant of the option that was chosen, and
is what this ADR now recommends. It should not be implemented until the owner
confirms, because it moves the cost from retrieval to the planner and that was
the axis the original three options were costed on.

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
