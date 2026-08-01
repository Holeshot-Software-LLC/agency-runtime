---
title: "AR-214: Preserve Codex product plan authority through context delivery"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-08-01
tags: [bug, product, codex, preflight, delegation]
related:
  - agency_runtime/core/preflight.py
  - agency_runtime/core/preflight_recipe.py
  - agency_runtime/core/codex_native_plan_scope.py
  - tests/test_product_host.py
  - tests/test_codex_activation_canary.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-214
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/211
depends_on: [AR-212]
blocks: [AR-203, AR-204, AR-215]
---

# AR-214: Preserve Codex product plan authority through context delivery

## Problem

Exact installed build `1694d6e07e04fb1c1f19f65bf2af381542b8079f`
passes the default full-suite install and supported autonomous activation. Its
one governed `python-cli-service` product trial reaches an inference-authored
planner repair and an applied recruiter response, then fails inside
`context_delivery` with a validation error before the route, exact unit plan,
specialist references, or Codex native plan scopes can commit atomically.

The parent therefore launches no specialist, writes no workspace proof, and
produces no final header. A generic `context_delivery_failed` receipt is not
enough to distinguish a malformed replay recipe from an invalid exact Codex
workspace-write authority projection without retaining sensitive content.

## Current state

Trial `ar212-1694d6e-readme-01` remains consumed and terminal `NO-GO`. Session
`019fbb37-41ed-70e3-b211-5affbafb53c6`, trace
`019fbb37-426b-7581-97e5-38f727e79327`, and run
`6a4eaea4-e69c-4c4c-964c-0dedd23f390a` retain one rejected and one applied
planner attempt followed by an applied recruiter attempt. Preflight then records
`stage=context_delivery`, `reason_code=context_delivery_failed`, and
`exception_category=validation_error`. Atomicity correctly leaves zero routes,
unit plans, specialist loads, grants, delegations, worker runs, finalizations,
or workspace writes. Correction count is zero because parent generation never
began.

A provider-free accepted-staffing fixture now reproduces that exact boundary.
The product prompt's standalone prose `/` was parsed as an absolute filesystem
resource, while Markdown-wrapped requested artifacts and the proof dotfile were
not normalized. Exact Codex scope validation therefore rejected the inferred
workspace-write plan before the atomic ready commit.

The local repair replaces the ambiguous product-prompt separator, recognizes
paired Markdown backticks and safe relative dotfiles, and preserves `/` as an
invalid explicit authority rather than silently broadening it to the repository.
Failure receipt schema v3 records the content-free
`native_plan_scope_invalid` invariant. A real schema-v41 migration fixture
proves existing rows acquire an empty invariant without losing evidence.

Local review and verification are green: the legacy fixture fails atomically
with zero route, scope, specialist, or delegation rows; the repaired fixture
commits all five inference-authored units and five exact scopes. The named
production spine passes 641 tests with 6 skips, product contracts pass 33/33,
dashboard tests pass 110/110, every routing gate passes, and decision
conformance kills every curated mutation with `source_unchanged=true`. Exact
build `d6ba36a` is installed and its activation passes, but its product trial
stops earlier in workforce routing. AR-215 owns that blocker, so the product
trial does not yet exercise this repaired context-delivery boundary.

## Approach

1. Reproduce the accepted multi-unit workspace-write plan through a focused
   unmocked preflight fixture without another live trial.
2. Preserve one bounded allowlisted context-delivery invariant code so malformed
   recipe, context-envelope, specialist-reference, and native-plan-scope failures
   remain distinguishable without prompt, response, path, or exception text.
3. Repair only the proven invariant while preserving inference-owned staffing,
   exact per-unit path authority, atomic ready commit, and fail-closed behavior.
4. Review and merge one new exact build, then run at most one fresh product trial.

## Dependencies

AR-212 is merged and proves recruiter verification now converges. ADR-0116,
ADR-0126, and ADR-0128 govern workspace proof, product delegation authority,
and opaque Codex child plan binding.

## Acceptance

- [x] A focused fixture reproduces the exact accepted-staffing to
  context-delivery validation failure without provider or live-host calls.
- [x] Terminal evidence identifies one bounded context-delivery invariant and
  retains no prompt, provider response, path, exception, or credential content.
- [x] The repaired recipe preserves every inference-authored unit and derives
  exact least-authority Codex workspace-write scopes without broadening to `.`.
- [x] Atomic failure still persists no route, unit plan, grant, or delegation.
- [x] The named local gate and focused review pass on one exact head.
- [ ] One new exact build passes default install, supported activation, and one
  governed product trial with specialist delegation, workspace write, a
  first-pass valid header, zero corrections, and independent artifact checks.
