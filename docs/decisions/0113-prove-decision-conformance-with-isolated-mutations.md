---
title: "Prove decision conformance with isolated curated mutations"
status: accepted
category: decisions
created: 2026-07-29
updated: 2026-07-29
tags: [testing, mutation-testing, routing, workforce, evidence]
related:
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0113
type: decision
deciders: [maintainers]
---

# ADR-0113: Prove decision conformance with isolated curated mutations

## Context

Agency has extensive example-based tests and quantitative routing gates, yet a
green suite does not by itself prove those tests would reject the specific
implementation reversals that previously bypassed online inference, promoted a
deterministic role anchor over an inference ranking, or overflowed contractor
schema boundaries. The same proof must reject amendment identity drift and
unbounded additive projection without turning model-authored target selection
into deterministic routing. Broad mutation tools are too slow for the named fast gate,
and mutating the owner checkout with Git-based restoration can overwrite work
or turn restoration failure into data loss.

The open-source `rollinsio/beyond-test-coverage` project demonstrates a useful
bounded pattern: deliberately introduce a small set of representative defects
and require the responsible tests to fail. Agency needs stricter evidence and
filesystem semantics than that project's general-purpose harness.

## Decision

Agency maintains a small, reviewed decision-conformance manifest. Each entry
names one product invariant, one exact source anchor and replacement, and one
test node that must kill the mutation.

The evaluator first runs every named test against an unmodified private copy.
Only a green baseline admits mutation evidence. It then creates a fresh private
copy per mutation, requires the anchor to occur exactly once, applies the
replacement there, and invokes the single named test. A mutation is killed only
when pytest reports an ordinary test failure and names that expected node.
Success, timeout, stale anchors, collection or usage errors, and failure of any
other test are all gate failures.

The evaluator never edits the requested checkout, never relies on Git to
restore files, never imports mutated modules into its own process, rejects
linked or reparse-point package inputs, and emits a bounded content-free JSON
report. It fingerprints the copied package and selected test inputs before and
after the run. The curated command includes both new-hire and amendment
decision boundaries and belongs in the named fast production gate; exhaustive
mutation fanout remains optional diagnostics.

## Consequences

- Tests carry executable proof that they distinguish the intended decision
  from known dangerous alternatives, not merely that they execute the code.
- The gate stays fast and reviewable because mutations correspond to explicit
  Agency invariants rather than arbitrary syntax changes.
- Exact anchors intentionally fail closed when implementation shape changes;
  updating a stale mutation requires reviewing its invariant and responsible
  test together.
- Copying source and tests costs modest local I/O but protects owner work and
  makes cleanup independent of Git state.
- This gate complements coverage, lint, routing evals, and hosted matrices; it
  does not replace them or establish comparative product quality.

## Alternatives

- **Run exhaustive mutation testing in every PR.** Rejected for the named fast
  gate because runtime and diagnostic volume are unbounded relative to the
  small set of product decisions that need explicit protection.
- **Mutate the owner checkout and restore with Git.** Rejected because dirty
  files, interrupted execution, and restoration errors can overwrite user work.
- **Treat any nonzero child exit as a killed mutation.** Rejected because
  collection failures, timeouts, and infrastructure errors do not prove test
  sensitivity.
- **Rely on coverage and green regressions.** Rejected because neither proves
  that the suite turns red when the protected decision is reversed.
