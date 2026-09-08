---
title: "AR-284 separate provider fallback counts from stage order"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [receipts, inference, compatibility]
related:
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
  - docs/roadmap/acceptance/evidence/AR-284-attempt-accounting-20260908.md
  - docs/roadmap/handoffs/issue-AR-284.md
  - docs/decisions/0238-separate-provider-fallback-accounting-from-stage-order.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 3fb97e7dc1ebcbf91e87036b033a1b9274f5c6e7
short: 3fb97e7d
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
---

# Worklog detail: Separate provider fallback counts from stage order

Source/records commit `3fb97e7dc1ebcbf91e87036b033a1b9274f5c6e7`, exact
subject `fix(receipts): separate provider fallbacks from inference-stage order (AR-284)`.
The immediate following worklog-only commit records this checkpoint. Capsule
metadata preserves the inherited clean floor; the source blob table identifies
the exact reviewed runtime and written regressions without self-reference.

## Purpose

Correct misleading telemetry that counted independent staffing/hiring stages
and semantic retries as provider fallbacks, without altering inference behavior.

## Approach

Stamp dispatch facts at both structured provider-chain loops; preserve
independent configured index and flattened ordinal. Three wrapper writers use
only validated counts or SQL NULL. Existing durable JSON carries optional
versioned stage/accounting metadata. The column already accepts NULL, so no
migration or historical rewrite is necessary. Preserve callback semantics.

## Challenges encountered

A configured provider index is not a count of actual calls, because entries
may refuse before dispatch. Bare None also does not prove a call occurred.
Unknown earlier entries therefore propagate uncertainty. Existing tests had
encoded the bad flattened count and were updated but deliberately not run.
Initial Ruff corrected two import-order findings. Context telemetry crossed
the clean-checkpoint threshold; this pair preserves the smallest coherent
source/records slice without a provider or test detour.
The first static documentation pass identified newly mapped AR-284 still in
pre-tracker history and inherited merge e790c4d4 missing its worklog row. Both
maintenance obligations were corrected; neither was a runtime test failure.

## Decisions and alternatives

ADR-0238 defines exact meanings. Reject inferred counts, unconditional zero,
historical backfill and unnecessary schema migration. Generic wrapper explicit
None is preserved; omitted defaults and callback behavior are not broadened.

## Verification

Targeted Ruff lint/format and diff checks only; written focused regressions
remain unrun under owner direction. No pytest, CI, native/model call, owner
database/profile change, install or acceptance verdict. Static record checks
do not imply runtime verification.
Final static documentation validation with required trackers passed for
1,279 Markdown files; metadata check matched that count. Ruff lint passed and
all 12 touched Python files were already formatted. Diff check was clean.

## Follow-ups

Parent coordinates source review and normal PR publication; test execution
and installed evidence await authorization. Tracker #754 is mapped and original
acceptance requirements are retained, unchecked. Old unversioned SQL wrapper
counts remain ambiguous and uninstrumented producers remain unknown.
