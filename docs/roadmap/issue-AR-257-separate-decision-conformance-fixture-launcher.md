---
title: "AR-257: Separate decision-conformance runner and trusted fixture launcher"
status: done
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [testing, security, decision-conformance, windows, critical-path]
related:
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_decision_conformance.py
  - tests/runtime_support.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-257
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-256]
---

# AR-257: Separate decision-conformance runner and trusted fixture launcher

## Problem

The checkout-local decision-conformance evaluator uses its pytest runner as the
`AGENCY_CI_PYTHON` fixture launcher. In a Windows workspace virtual environment,
that executable can inherit cross-account Modify access from the collaborative
checkout. Production launcher validation correctly rejects it, so the required
83-mutation gate stops at the OpenClaw baseline even though the focused test
passes outside the evaluator.

## Current state

The failure predates AR-256 and is reproducible at its clean ancestor
`b79a4138`. The exact installer result was `failed_step=launcher_identity` with
`executable parent namespace permits cross-account substitution`. The evaluator
now keeps pytest on the selected workspace runner while independently resolving
and validating the persistent fixture launcher. Production namespace
enforcement remains unchanged.

## Approach

Keep the selected evaluator interpreter as the pytest runner. Independently
select and validate a persistent fixture launcher using the existing executable
identity boundary, then export only that trusted path as `AGENCY_CI_PYTHON` to
the least-privilege subprocess. Preserve source-root exclusion and add a
regression for a runner below a cross-account-modifiable checkout.

## Dependencies

- ADR-0055 defines the executable namespace and frozen-identity boundary.
- AR-256 cannot reach its required clean checkpoint until decision conformance
  can evaluate the current checkout without weakening that boundary.

## Verification

The final independent-runner/fixture API completed its checkout-local evaluator
on 2026-08-12 with exit zero: baseline passed in 173,427 ms, all 83 curated
mutations were killed, zero survived or were invalid, and
`source_unchanged=true`. Focused regressions cover default separation, exact
explicit validation, and fail-before-copy behavior. The globally installed
`agency.exe` is an older 0.1.0 projection and remains an environment/tooling
mismatch; verification invokes the current checkout directly and does not
install or trust a projection.

## Acceptance

- [x] The evaluator may run pytest through a workspace virtual environment
      without using that path as a persistent installer fixture launcher.
- [x] `AGENCY_CI_PYTHON` names an independently validated persistent
      interpreter, while source-root exclusion and least privilege remain in
      force.
- [x] A platform-independent regression models a non-current workspace venv and
      a distinct trusted fixture launcher; an unsafe explicit fixture fails
      before any private copy or pytest launch.
- [x] The focused decision-conformance tests and the full curated 83-mutation
      gate pass with `source_unchanged=true`.
- [x] Local documentation, worklog, and roadmap traceability agree; tracker
      creation remains explicitly authorization-pending and is not represented
      as present.
