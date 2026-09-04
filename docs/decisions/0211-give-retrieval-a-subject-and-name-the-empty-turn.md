---
title: "Give retrieval a subject and name the empty turn"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, retrieval, routing, receipts, evals, observability]
related:
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/handoffs/issue-AR-383.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0211
type: decision
deciders: [owner]
---

# ADR-0211: Give retrieval a subject and name the empty turn

## Status

**Accepted 2026-09-04.** Item 3 of the AR-383 capsule's next package, filed as
AR-370. Criteria 3 to 6; criterion 1's live proof is outstanding.

## Context

Retrieval ran on the user's literal text. Operational requests scored 0.0
across the entire roster -- "Install ripgrep on this machine", "Restart the
dashboard service", "configure the gateway" -- and the zero-score result was
not empty but alphabetical: `3d-scene-developer` was top-three for 20 of 30
prompts and top-1 for 7.

`_DOMAIN_EXPANSIONS` was the layer meant to close that gap. It was a
hand-curated table of about twenty-five nouns, nearly all specific to one
operator's stack (`openclaw`, `hermes`, `litellm`, `systemd`, `telegram`,
`vllm`, `rocm`), shipped to every installation, with no entry for any common
operational verb. Owner direction on 2026-09-02 was explicit: the expansion
table is the wrong architecture, and no user should have to phrase a request in
card vocabulary to get staffed.

Three further things were wrong beside it. A request whose subject is a bare
deictic or a bare URL has nothing retrievable in it at all, and the runtime
handed the raw words to retrieval anyway. An unstaffed turn reported one
outcome for three different failures, which is why this read as a recruiter
defect for weeks. And the graded routing corpus could not show any of it: every
work case in it was already phrased in card vocabulary, so the failure this
issue describes could not appear in the eval.

## Decision

1. **The expansion table is retired.** `expand_query` and
   `domain_expansion.py` are deleted and the routing query is the affirmative
   intent of the refined message. The typed work statement the planner derives
   -- ADR-0197's zero-signal trigger, reaching recall as `inferred_work_subject`
   under ADR-0208 -- is what states the work now, and it is stack-neutral by
   construction. `agency explain` keeps its `domain_expansion` block, reporting
   `applied: false` and `retired: true`, rather than the field vanishing under
   readers of that payload.

2. **A bare reference is resolved from the turn itself, before retrieval.** A
   URL resolves to its own distinctive labels, with the parts every URL carries
   dropped; a deictic resolves to the typed subject hints the previous turn
   derived. Nothing is invented and no inference call is made: this supplies a
   subject, and naming the work remains the planner's job.

   Whether a request still names a subject once its bare reference is removed
   is asked with `retrieval_has_signal`, the same predicate the zero-signal
   trigger uses. Deciding it locally would have meant shipping a list of words
   that do not count as a subject, which is the curated vocabulary this ADR
   removes. That predicate is a full pass over the eligible catalog, so it is
   spent only on turns that contain a URL or a deictic at all.

3. **The routing receipt records the resolution.** `reference_resolution`
   carries whether the subject was a bare reference, which kind, where it was
   resolved from, and the bounded identifiers it resolved to, so a wrong
   resolution is visible rather than silently steering retrieval.

4. **An unstaffed turn says which kind it was.** `request_underspecified` when
   neither the message nor the derived subject named anything retrievable;
   `no_relevant_candidate` when retrieval ran against a real subject and
   returned nothing; and the existing `no_safe_sufficient_team` when the
   recruiter judged a real candidate set. Only the third is a recruiter
   verdict. The codes ride on the staffing decision's abstention reasons, the
   same route `workforce_credential_env_unset` takes to the receipt and the
   fail-open disclosure.

5. **The corpus carries a case per operational verb.** The corpus catalog had
   no card covering installation, service restart or monitoring setup, so those
   verbs could not retrieve a correct answer however good retrieval became;
   `service-operations-engineer` and `monitoring-engineer` are added and the
   corpus moves to 1.5.0. Each case is phrased as a work statement, because the
   eval is deterministic candidate recall and cannot make an inference call: a
   case in the user's raw words would measure the inference stage's absence
   rather than retrieval's behaviour. What the cases guard is the property the
   fix depends on -- that retrieval answers correctly once the query states the
   work.

## Consequences

The eight operational verbs the issue measured now retrieve their specialist at
rank one, where seven of eight previously retrieved nothing. The corpus grew
from 37 cases over 16 cards to 45 over 18, and every published threshold still
passes with room: candidate precision@3 rose from 0.6071 to 0.6364, required
recall@3 and top-1 relevance are both 1.0, and the forbidden rate stays 0.

The new `service-operations-engineer` card first displaced `technical-writer`
as top-1 on the existing `route-readme` case, because a bare "installation"
also matches "rewrite the README installation guide". Its nouns were changed to
host-side verbs rather than the noun, which restored that case; the card is
described in terms of what it does to a host, which is the distinction that
matters.

Gating the resolution behind a cheap URL-or-deictic precheck was not
cosmetic: without it the catalog pass ran on every request and the routing
eval's cache-hit p95 went from 0.19 ms to about 70 ms.

Criterion 1's live proof is outstanding. Its mechanism is in place and the
deterministic half is measured here, but "configure the gateway" and
"install this: <url>" retrieving a relevant specialist end to end needs a
staffed turn against the live roster.

Nothing here selects, ranks or filters a specialist. The change is in what
retrieval is asked, and in what the runtime says when it comes back empty.
