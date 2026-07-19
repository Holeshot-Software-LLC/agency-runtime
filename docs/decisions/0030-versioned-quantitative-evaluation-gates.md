---
title: "Gate routing changes with versioned quantitative evaluation"
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-11
tags: [routing, evaluation, performance]
related:
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0030
type: decision
deciders: []
---

# ADR-0030: Gate routing changes with versioned quantitative evaluation

## Context

Unit tests can prove individual branches without showing whether routing is
accurate across a representative corpus, whether policy phrases overmatch
adversarial examples, whether delegation detection is balanced, or whether a
large roster remains fast. Unversioned examples and machine-specific benchmark
claims are difficult to compare over time.

## Decision

Maintain a versioned, offline deterministic corpus and report schema. Run it
with `agency eval routing`; support machine-readable JSON and an option to omit
per-case details. The v1.1 corpus contains routing, adversarial policy, and
delegation-detection and dependency-graph cases plus a generated 1,000-agent
narrowing benchmark.

The v1.1 release-regression gates are:

- routing precision@3 at least 0.75, required recall@3 at least 0.97, top-k
  accuracy at least 0.95, top-1 accuracy at least 0.90, forbidden-case rate
  zero, and abstention accuracy 1.0;
- policy macro F1, required recall, and case accuracy at least 0.95 with zero
  forbidden cases;
- delegation precision at least 0.95, recall at least 0.90, decision accuracy
  at least 0.94, count/source accuracy at least 0.90, and dependency-graph
  accuracy 1.0;
- deterministic 1,000-agent narrowing with measured p95 no greater than 20 ms
  and full-pipeline cache-hit p95 no greater than 2 ms; and
- at least 40 concurrent calls per second with observed overlap of at least two,
  deterministic selections, and a fresh trace for every cached request.

Keep metric definitions, corpus version, report version, and thresholds in the
repository. A material corpus, metric, or threshold change requires a version
change and an updated decision record. Record actual values in CI/release
evidence rather than hard-coding one developer machine's timing into public
claims.

These gates are a regression floor. The corpus remains intentionally small, so
larger stress runs and reviewed real-world failures should extend it without
silently changing the v1 metric definitions or thresholds.

## Consequences

- Routing changes have a stable quantitative comparison point.
- Zero-signal abstention and forbidden matches are first-class correctness
  outcomes.
- The performance threshold includes CI headroom and therefore does not replace
  profiling or a stricter production service-level objective.
- The small curated corpus can miss real-world distributions; new failures
  should become reviewed cases rather than ad hoc exceptions.
- Release automation can fail on gate regressions without calling a network
  model or exposing prompts.

## Alternatives

- Rely only on unit tests. Rejected because branch coverage is not system-level
  quality measurement.
- Use a live model judge in the release gate. Rejected because network,
  provider, and stochastic behavior would make the baseline irreproducible.
- Publish only a latency number. Rejected because fast incorrect routing is not
  useful.
- Change thresholds without versioning. Rejected because historical reports
  would no longer be comparable.

## Provenance

The production-readiness refactor added the versioned corpus, deterministic
metrics, graph-accuracy gate, CLI report, adversarial cases, and 1,000-agent
benchmark. The
implementation commit is recorded through the worklog after it is created.
