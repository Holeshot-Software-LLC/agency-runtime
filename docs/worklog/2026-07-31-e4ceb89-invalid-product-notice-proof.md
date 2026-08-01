---
title: "Worklog detail: Fail closed on invalid product notice proof"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, product, evidence, security, mutation]
related:
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
  - docs/decisions/0125-admit-only-exact-content-free-codex-host-notices.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e4ceb89
short: e4ceb89
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
---

# Worklog detail: Fail closed on invalid product notice proof

## Purpose

Close the late PR 201 review defect that allowed malformed Codex host-notice
evidence to disappear from the rendered collaboration projection without
invalidating the product verdict.

## Approach

Make a valid product collaboration projection an explicit Agency-mode Codex
proof gate. When the validated projection is unavailable, retain `null` in the
content-free invocation evidence, add one exact failure, and prevent the proof
from passing.

Extend the existing malformed-notice parameter set through the complete proof
evaluator instead of testing only the projection helper. Add a curated mutation
that removes the new pass gate; the focused regression must kill it.

## Challenges encountered

The original projection validation was locally correct but disconnected from
the final pass predicate. The product could therefore report a successful
runtime contract with no publishable collaboration evidence. The review arrived
after PR 201 had merged, so AR-208 and tracker #200 had to be reopened.

The same review also reported a ledger ancestry problem. Canonical Git evidence
disproved that finding: `ea376a5`, `947dafb`, `bb1122c`, and `096570a` are all
ancestors of reviewed head `57fba809` and merge `dd85e7d`.

## Decisions and alternatives

Keep the projection validator as the single shape-validation boundary and make
its result authoritative for the verdict. Duplicating host-notice checks inside
the activation graph validator was rejected because the projection still could
drift independently.

## Verification

- `tests/test_product_host.py`: 21 passed warning-strict.
- Focused invalid-notice cases: 7 passed warning-strict.
- `product-proof-allows-invalid-host-notice-projection`: killed; baseline passed;
  source unchanged.
- Focused Ruff and documentation validation passed.

## Follow-ups

Run the named fast spine before marking AR-208 complete, then reply to and
resolve both PR 201 threads with exact commit and verification evidence.
