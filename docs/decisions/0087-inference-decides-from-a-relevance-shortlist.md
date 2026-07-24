---
title: "Inference decides specialist selection from a relevance shortlist"
status: accepted
category: decisions
created: 2026-07-23
updated: 2026-07-23
tags: [routing, workforce, selection, inference, AR-119]
related:
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/workforce/capability_ontology.py
supersedes: []
superseded_by: null
id: ADR-0087
type: decision
deciders: [maintainers]
---

# ADR-0087: Inference decides specialist selection from a relevance shortlist

## Context

The north-star behavior (AR-119) is: for any user ask, give the agent the
*best* specialist for that exact ask, or hire a contractor when no employee
fits. This must beat the stock upstream semantic selector, which is a
deterministic token matcher and therefore returns generic or missed matches
for specialized intent (for example, a React specialist force-fitted to a
FluxUI request, or an empty selection for an obvious code review).

Two facts forced this decision:

1. The whole workforce is large (263+ specialists and growing; contractors
   are added at runtime). Passing every contract to inference per turn is
   neither performant nor bounded.
2. Pure deterministic selection is the failure mode this project exists to
   avoid: rigid keyword templates return generic matches, abstain on
   unmodeled intent, and cannot distinguish "review an auth refactor" from
   "review a doc update." Determinism as the *decider* is what makes the
   runtime no better than the upstream baseline.

A concrete regression exposed the gap: the deterministic fallback emitted
bespoke capability strings (`review-diffs`, `repository-map`) that lived in
neither the workforce contract vocabulary nor the capability ontology, so no
contract could ever match and selection was empty for *every* ask when
inference was unconfigured. Fixing that one bug is necessary but not
sufficient; the durable question is *who decides* specialist fit.

## Decision

Specialist selection is a two-stage funnel with **inference as the decider,
determinism as the recall filter**:

1. **Recall (deterministic, per-ask).** Reduce the whole workforce to the
   set of specialists whose typed contracts are *plausibly relevant* to the
   ask's typed work units (capability, lifecycle, domain, stack, authority).
   The inclusion rule is **zero false negatives**: any specialist who could
   plausibly fit is kept. A soft token cap (default `MAX_DETAIL_CARDS`,
   currently 12) trims only an oversized relevant set by relevance score;
   it is never an arbitrary fixed width. This stage never decides who is
   best.

2. **Decide (inference, bounded).** The relevance shortlist plus the ask
   goes to the model. Inference picks the best specialist for the *actual*
   intent, or declares a real gap ("none of these fits; the need is X").
   One small, bounded, cacheable call. This is where the runtime beats the
   stock selector: the model reads the real intent against real specialist
   descriptions.

3. **Gap hires.** When inference declares a gap, that declaration is the
   contractor specification; `hire_contractor_for_gap` builds and admits a
   contractor for exactly that need in the causing turn. A generic employee
   is never force-fitted to a real gap.

The deterministic path is the **degraded fallback** only when inference is
genuinely unavailable (no configured provider). In that mode it must still
select a defensible specialist via the typed matcher rather than abstain to
an empty selection, but it is explicitly not the product.

The capability vocabulary is governed at one place
(`workforce/capability_ontology.py`): the workforce contracts use the
`CORE_CAPABILITY_IDS`, the deterministic fallback derives each work unit's
required capability from its `artifact_kind` through one unified
`ARTIFACT_CAPABILITY` map, and no bespoke per-unit capability strings bypass
that map. New specialists and contractors are inherently discoverable
because recall reads the live roster index, not a static keyword list.

## Consequences

- Selection is intelligent and per-ask when a provider is configured: the
  best specialist for the exact intent, or a hired contractor on a real
  gap. New agents and contractors become selectable the moment they enter
  the roster, with no vocabulary or code change.
- Latency and cost are bounded: inference sees a shortlist, not the whole
  roster. The cold-selection gate (currently 15000 ms) holds as the budget;
  the soft cap is tunable from measured provider evidence, not guesswork.
- The deterministic fallback is honest but bounded: offline, it picks a
  typed-match specialist instead of abstaining, and never claims to be the
  intelligent selector. Tests that run offline exercise this fallback.
- The capability ontology is the single source of truth for
  artifact-to-capability derivation; the prior duplicate map in
  `inference._ARTIFACT_CAPABILITY` is removed to eliminate the
  `architecture-record` / `test-evidence` disagreement.

## Alternatives

- **Determinism as primary selector** (richer typed matching, inference only
  for hard-to-type asks). Rejected: it caps "best specialist" at what static
  types can express and cannot distinguish specialized intent; it is the
  generic-match behavior this project exists to beat. Determinism is kept
  only as recall and as the degraded fallback.
- **Govern the bespoke planner capabilities (`review-diffs`, etc.) as a new
  vocabulary or refinement map.** Rejected: it would enshrine the fallback's
  rigid keyword templates as permanent ontology, block runtime
  discoverability of unmodeled specialties (e.g. FluxUI), and contradict the
  inference-decides model. The bespoke strings are removed; descriptive
  detail already lives in the typed unit fields (`artifact_kind`,
  `lifecycle_phase`, `outcome`).
- **Pass the whole roster to inference.** Rejected: unbounded latency and
  cost, and unnecessary — the relevance shortlist preserves the candidates
  that matter.
