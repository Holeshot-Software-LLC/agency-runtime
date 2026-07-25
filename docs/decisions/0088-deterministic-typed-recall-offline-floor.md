---
title: "Deterministic typed-recall is the offline floor"
status: accepted
category: decisions
created: 2026-07-24
updated: 2026-07-24
tags: [routing, workforce, selection, inference, offline, AR-119]
related:
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/fallback.py
supersedes:
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
superseded_by: null
id: ADR-0088
type: decision
deciders: [maintainers]
---

# ADR-0088: Deterministic typed-recall is the offline floor

## Context

ADR-0087 made inference the sole specialist decider and removed the
deterministic decider from the runtime. It also specified that when no provider
is configured the runtime **declines** — it injects no Agency specialist and
hands the turn to the host's native capability. The reasoning was sound:
deterministic selection cannot read intent, so a keyword-luck pick is worse than
no pick.

In practice the decline is too strict for a tool that should "still work." An
operator who has not yet configured a provider gets **zero** routing value from
Agency: every turn declines, even asks that an obvious typed specialist covers.
The experience is "Agency does nothing until you configure inference," which
undermines the value proposition and the first-run experience.

Two facts make a middle path possible:

1. The deterministic **typed-recall** layer (stage 1 of the inference pipeline)
   is genuinely better than the "keyword-luck" decider ADR-0087 rejected. It
   matches on typed contract fields — artifact kind, lifecycle phase, domain,
   stack, capability IDs, authority — runs coverage scoring, promotes role
   anchors, and enforces the same composition/conflict/eligibility rules as the
   inference path. It is not the upstream token-matcher; it is structured typed
   matching that already feeds the recruiter.
2. The upstream audited-roster asset worth borrowing is the **roster**
   (audited specialists, already synced), not its selector. ADR-0087 states this
   explicitly. Community updates arrive through roster sync, not through a
   vendored selector.

## Decision

When no inference provider is configured, the runtime runs the deterministic
typed-recall layer as an **offline floor** instead of declining:

1. `deterministic_work_plan` produces a typed work-unit plan (keyword → typed
   units, no inference).
2. Whole-roster typed recall + role-anchor promotion + `verify_staffing`
   (coverage/composition/eligibility/budget) form the smallest compatible team.
3. If a safe team forms, Agency accepts it and stamps the outcome
   `inference_mode="deterministic"`, `decision_source="deterministic"` —
   never mistaken for an inference pick.
4. If the floor abstains (trivial/ambiguous request, or no safe team), Agency
   injects no specialist and hands the turn to the host's native capability
   (`inference_mode="deterministic_abstained"`, `decision_source="none"`).

The recruitment source is surfaced as a **machine-reliable "Recruited via"**
stamp — in the structured routing evidence, the dashboard, `agency explain` /
`--json`, and as a new line in the response header — distinct from the
model-authored "Why" line. An operator can tell at a glance whether a specialist
was recruited by `inference`, `deterministic`, `cached`, or `none`.

**This decision supersedes only ADR-0087's offline-decline clause.** It does
not change ADR-0087's core: when a provider IS configured, inference remains the
sole decider (plan → broad typed recall → recruiter nominates best or declares
gap → verify → gap hires a contractor). The deterministic decider is still not a
runtime selection path when inference is available; it is the offline floor
only.

## Consequences

- Agency provides value without a configured provider: a best typed-guess
  specialist for obvious asks, stamped `deterministic` so its lower quality
  (cannot read intent) is honest and visible. Operators who want the
  intent-aware path configure a provider.
- The "Recruited via" stamp makes recruitment source explicit everywhere, so no
  deterministic pick is ever mistaken for an inference pick and no decline is
  mistaken for a selection.
- Offline routing is strictly worse than inference (typed matching cannot read
  intent) but strictly better than the upstream token-matcher (typed fields +
  coverage + composition vs. keyword luck) and strictly better than declining.
- The roster — not the selector — remains the community-sync asset; no upstream
  selector is vendored.

## Alternatives

- **Keep declining offline (ADR-0087 as written).** Rejected: Agency adds zero
  routing value without a provider, which is a poor first-run and degraded-mode
  experience. The typed-recall layer makes a better floor available at no
  correctness cost.
- **Vendor the upstream selector as the offline floor.** Rejected:
  ADR-0087 explicitly rejected the upstream selector ("enshrines the known-shit
  deterministic behavior"). Our typed-recall layer is already a better offline
  router than the upstream token-matcher, and the roster is already synced for
  community updates. Vendoring the selector would re-introduce the exact
  keyword-matcher we removed.
- **Add a 7th response-header line vs. structured-only stamp.** Chosen: both.
  The 7th header line makes the source visible mid-conversation; the structured
  stamp makes it available to tooling. The header contract grew from six to
  seven fields; parsers/validators iterate the field list, so the change is
  additive.
