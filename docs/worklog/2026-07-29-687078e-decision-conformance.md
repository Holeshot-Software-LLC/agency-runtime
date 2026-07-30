---
title: "Worklog detail: Make decisions diagnosable and mutation-conformant"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [workforce, hiring, diagnostics, mutation-testing, inference]
related:
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/handoffs/issue-AR-200.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 687078e
short: 687078e
date: 2026-07-29
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/176
related_issues:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
---

# Worklog detail: Make decisions diagnosable and mutation-conformant

## Purpose

Replace the generic post-parse contractor failure with evidence-safe validation
stages, repair the confirmed employment-to-workforce Unicode byte-boundary
mismatch, and prove that focused tests reject the known inference, ordering,
contract-boundary, and diagnostic regressions.

## Approach

The hiring path keeps the complete validated employment contract for specialist
prompt compilation while normalizing and UTF-8 byte-bounding only the smaller
workforce routing projection. Validation exceptions are translated into
allowlisted content-free stage codes before they enter routing evidence.

The decision-conformance evaluator proves a green baseline, rejects linked or
reparse-point package inputs, copies only required inputs into an owner-private
directory, and applies each exact mutation to a fresh copy. A mutation is
killed only when pytest returns its ordinary assertion-failure exit and names
the one expected test node. It never mutates or restores the owner checkout.

## Challenges encountered

The live generic failure reduced to a character-versus-byte contract mismatch:
160 valid Unicode characters can exceed the destination's 192-byte routing
field. During review, the first disposable-copy implementation was also found
to preserve source symlinks. The final implementation fails closed on symlinks
and Windows reparse points and has a dedicated regression test.

## Decisions and alternatives

The gate adapts the mutation-sensitivity principle from
`rollinsio/beyond-test-coverage` without copying its in-place Git restoration
model. ADR-0113 records the bounded curated manifest, exact-node kill criteria,
private-copy isolation, and the explicit prohibition on treating timeouts or
infrastructure failures as successful kills.

## Verification

- Focused workforce, inference, selection, CLI, and conformance suite: 108
  passed, 1 skipped, 1 expected xfail.
- Named fast Python spine: 668 passed, 6 skipped.
- Dashboard UI: 109 passed.
- Routing evaluation: every correctness, policy, delegation, latency, and
  263/1,000/10,000-agent scale gate passed.
- Decision conformance: green baseline; 5 of 5 mutations killed; 0 survivors;
  0 invalid results; source inputs unchanged.
- Documentation validation: 536 Markdown files passed.
- Ruff lint, Ruff format, and Git diff checks passed.

## Follow-ups

Push and merge the PR, exact-install the merged revision for Codex and ZCode,
run one bounded ordinary Codex canary, and publish its prompt, specialist,
delegation, model-receipt, correction-count, and mutation evidence to the local
shareable AR-200 report.
