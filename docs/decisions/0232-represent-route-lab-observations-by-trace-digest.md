---
title: "Represent Route Lab observation correlation by the trace digest"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, diagnostics, correlation, acceptance]
related:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/acceptance/issue-AR-173.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/observability.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
superseded_by: null
id: ADR-0232
type: decision
deciders: [maintainers]
---

# ADR-0232: Represent Route Lab observation correlation by the trace digest

## Context

First AR-173 review at f4f5124e satisfies 1/3/4/5 but contradicts criterion 2:
its original exact-trace wording conflates identity with representation.
The response holds a raw UUID; the content-free observation intentionally
holds its domain-separated SHA-256 digest. Both are deterministically joinable,
but they are not equal strings. First verdicts are preserved at 941b9025.
ADR-0231 corrected other obsolete clauses but left this sentence unchanged.

## Decision

Supersede ADR-0231 explicitly, preserving its accepted behavioral reconciliation:

1. Admitted enabled routing operations allocate a fresh UUIDv4 before explanation.
   Invalid and disabled requests do not fabricate routing traces.
2. The response carries that trace. The current request observation's
   correlation_digest equals correlation_observation_digest(response trace_id).
   No raw trace field is required in the observation, and request ID is separate.
3. Correlation observations stay bounded and content-free.
4. A real authenticated HTTP regression proves that exact digest relationship
   for the matching request and absence of durable diagnostic turn/routing rows.
5. ADR-0105's focused/current UI/named-spine/record gates apply; exhaustive
   integration remains optional.

Retain original criteria 1/2/4/5 in AR-173, the original narrative and all first
verdicts. Criterion 3 is unchanged. No production change follows this decision;
logging representation already has these semantics. Run all five criteria once
more against the explicit final candidate; do not copy earlier verdicts.

## Consequences

This corrects the record without adding raw identifiers to log envelopes or
inventing diagnostic turn writes. Existing two-request HTTP evidence exercises
the exact relationship, including fresh identities and no private content.
It does not promise disk persistence of the emitted logs or native activation.

## Alternatives

- Log the raw trace solely to satisfy the sentence: changes an established
  observation contract without improving correlation.
- Assert the digest and UUID are equal: factually false.
- Hide the contradicted verdict or silently amend ADR-0231: loses provenance.
- Retire the whole issue: discards a useful exact-request correlation regression.

## Verification provenance

b2da6eb9 adds the direct HTTP regression without production changes. First
review is preserved at 941b9025; all five final criteria satisfy at 594bc4d3
after this explicit representation correction. The
[worklog registry](../worklog/README.md) preserves their exact subjects and
related issue, with no third review or copied verdict.
