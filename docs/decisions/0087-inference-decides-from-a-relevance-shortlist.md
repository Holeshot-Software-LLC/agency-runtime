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
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/workforce/capability_ontology.py
  - agency_runtime/core/host_capabilities.py
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

**There is no deterministic decider.** Deterministic selection is
shit-by-nature at "best specialist for *this* ask" — it rests on keyword
luck and cannot read intent — so the runtime refuses to ship one. When a
provider is configured, inference is the sole decider (steps 1-3 above).
When inference is unavailable (no configured provider), the runtime
**declines to select**: it injects no Agency specialist and hands the turn
to the host's native capability. Declining is preferred over a bad pick —
offline produces *no* Agency value rather than *wrong* Agency value. The
prior deterministic fallback (`workforce/fallback.py` plan-and-staff
decider, `staffing_verifier` "optimal team" logic) is removed; only the
typed *recall* it performs survives, repurposed as stage 1.

The capability vocabulary is governed at one place
(`workforce/capability_ontology.py`): the workforce contracts use the
`CORE_CAPABILITY_IDS`, recall matches units to contracts on typed fields
(capability, authority, lifecycle, domain, stack), and no bespoke
per-unit capability string bypasses the ontology. New specialists and
contractors are inherently discoverable because recall reads the live
roster index, not a static keyword list.

## Consequences

- Selection is intelligent and per-ask when a provider is configured: the
  best specialist for the exact intent, or a hired contractor on a real
  gap. New agents and contractors become selectable the moment they enter
  the roster, with no vocabulary or code change.
- Latency and cost are bounded: inference sees a recall shortlist, not the
  whole roster. The cold-selection gate (currently 15000 ms) holds as the
  budget; the soft cap is tunable from measured provider evidence.
- Offline (no provider) declines: the runtime injects no Agency specialist
  and hands the turn to the host's native capability. Offline never
  produces a wrong pick — it produces no pick. This is preferred over a
  bad deterministic pick; Agency value requires a configured provider.
- The deterministic *recall* layer survives (typed shortlisting with zero
  false negatives) as stage 1; the deterministic *decider* is removed.
  Tests that asserted optimal specialist selection against the deterministic
  decider are converted to the inference path (the only place optimality is
  attainable or asserted).
- The capability ontology is the single source of truth for
  artifact-to-capability derivation; the prior duplicate map in
  `inference._ARTIFACT_CAPABILITY` is removed to eliminate the
  `architecture-record` / `test-evidence` disagreement.

## Alternatives

- **Determinism as primary or fallback selector** (a typed matcher that
  decides "best specialist"). Rejected: deterministic selection cannot read
  intent and its picks rest on keyword luck, so it is shit-by-nature at
  "best for this ask." Every reimplementation (the bespoke fallback here,
  the upstream selector, colleagues' rewrites) lands the same way because
  the approach, not the implementation, is the limit. Determinism is kept
  only as the recall filter (stage 1), never as a decider.
- **Use the upstream selector as the offline floor.** Rejected: that
  enshrines the known-shit deterministic behavior as a safety net. The
  upstream asset worth borrowing is the *pool* (ingested, audited,
  versioned specialists), not its selector. The pool is retained and grown;
  the selector is not vendored.
- **Govern the bespoke planner capabilities (`review-diffs`, etc.) as a new
  vocabulary or refinement map.** Rejected: it would enshrine rigid keyword
  templates as permanent ontology, block runtime discoverability of
  unmodeled specialties (e.g. FluxUI), and contradict the inference-decides
  model. The bespoke strings are removed; descriptive detail already lives
  in the typed unit fields (`artifact_kind`, `lifecycle_phase`, `outcome`).
- **Pass the whole roster to inference.** Rejected: unbounded latency and
  cost, and it degrades quality — the model chooses best among a few
  plausible candidates, not a crowd. The recall shortlist is what makes
  inference both good and fast.
