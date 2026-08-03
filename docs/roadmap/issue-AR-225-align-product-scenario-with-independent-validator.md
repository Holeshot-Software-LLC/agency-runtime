---
title: "AR-225: Align product scenario with independent validator"
status: open
category: roadmap
created: 2026-08-03
updated: 2026-08-03
tags: [bug, evaluation, product, contract, validation]
related:
  - agency_runtime/core/evals/product_scenarios.py
  - agency_runtime/core/evals/product_validation.py
  - tests/test_product_scenarios.py
  - tests/test_product_validation.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/analysis/2026-08-03-ar-203-readme-story-evidence.html
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-225
priority: p0
tracker_url: null
depends_on: [AR-223]
blocks: [AR-203, AR-204]
---

# AR-225: Align product scenario with independent validator

## Problem

The terminal `ar203-624a6a3-readme-01` product trial implemented the published
`python-cli-service` contract, passed its project tests, and produced all three
required files. Independent validation nevertheless failed because its hidden
probe requires a different, undocumented interface: global `--data PATH`
before the subcommand, `add --title TEXT`, and JSON records with a `title`
field. The published scenario says only that every command accepts `--data
PATH`; it does not specify option position, `--title`, or the record field.

This mismatch can reject a valid inference-authored product after Agency has
correctly selected, delegated, executed, and finalized the complete team. A
hidden evaluator contract must not be stronger than the prompt it grades.

## Current state

Exact build `624a6a398f4620eeb92e62193b1407a482941783` passed autonomous
activation and its sole product trial completed seven planned units, seven
delegations, seven exit-zero workers, and one accepted finalization. Workspace
write was proven without persistent trust mutation. Independent validation
found `app.py`, `tests/test_app.py`, and `README.md`; project tests and
documentation checks passed. Only `python-cli-workflow` and
`python-cli-errors` failed.

The generated CLI uses `add DESCRIPTION --data PATH`, stores `description`,
and emits that field. The hidden workflow invokes `--data PATH add --title
TEXT` and recognizes only `title`. That first mismatch prevents storage
creation, so the later invalid-ID probe also sees no persisted list or object.

The bounded source repair now publishes the exact shared probe contract for
both Python and TypeScript task CLI scenarios: global `--data PATH`, exact add,
list, and complete forms, task fields, accepted list shapes, and unknown-ID
storage preservation. The independent validator remains unchanged. The new
regression fails twice on the pre-fix prompt and passes after repair. All 11
scenario/validator tests and 50 directly affected product, CLI, context, and
workforce tests pass under warning-strict mode; focused Ruff, formatting, and
whitespace checks pass.

## Approach

1. Make the scenario prompt state one exact CLI grammar, JSON record schema,
   and list response shape that the independent validator can exercise.
2. Keep the validator independent, but derive or test every probe assumption
   against that public scenario contract so no hidden stronger requirement can
   recur.
3. Add a regression using a minimal implementation of the published contract
   and a mutation for each formerly hidden assumption.
4. Run focused product scenario/validation tests and the named fast spine
   before one new immutable build may consume another product trial.

## Dependencies

AR-223 proves actual Agency child workspace execution. AR-203 and AR-204 remain
blocked only because their final product verdict cannot accept an application
whose published and independently graded interfaces disagree.

## Acceptance

- [x] The `python-cli-service` prompt specifies the exact option placement,
  add-title input, task JSON fields, and list response shape used by validation.
- [x] Independent probes require no interface behavior absent from the
  published scenario.
- [x] Focused tests fail when prompt and validator contracts diverge and pass
  for one minimal conforming application.
- [x] Existing path, output-bound, timeout, artifact, and sandbox protections
  remain fail closed.
- [ ] Focused checks and the named fast spine pass before another immutable
  build or live product trial.
