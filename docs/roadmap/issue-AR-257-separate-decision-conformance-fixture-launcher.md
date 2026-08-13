---
title: "AR-257: Separate decision-conformance runner and trusted fixture launcher"
status: done
category: roadmap
created: 2026-08-12
updated: 2026-08-13
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

Candidate `45b21cdc` completed its expanded evaluator on 2026-08-13. It exited
zero in 883.1 seconds: baseline passed in 169,548 ms, all 131/131 mutations were
killed, zero survived or were invalid, and `source_unchanged=true`. That result
remains candidate-scoped history.

## 2026-08-13 expanded evaluator result for `211563c7`

The expanded evaluator then ran for candidate `211563c7` and **failed**. Its
baseline passed in 197,516 ms and 149 of 151 curated mutations were killed with
zero invalid and `source_unchanged=true`, but two survived. Both weaken
`_codex_uuid` in `agency_runtime/core/codex_spawn_provenance.py`, and both were
mapped to `test_session_identity_requires_non_nil_rfc_uuid7`:
`codex-rollout-allows-nil-uuid-identity`, which accepts the nil UUID, and
`codex-rollout-drops-observed-uuid-version-domain`, which accepts any UUID
version. The third mutation sharing that node,
`codex-rollout-drops-rfc-uuid-variant`, was killed.

The cause was measured rather than inferred. The rollout filename embeds the
current thread identity, and `_rollout_filename_residual_seconds` derives its
UTC clock from that identity's UUIDv7 timestamp bits, so a nil or non-v7
session identity is already refused by the clock residual before its UUID
domain matters. All three identities in that test were filename-bound, so the
test could not observe the identity rule it names. Only the bad-variant case,
which preserves the exact timestamp bits, discriminated — which is why the
variant mutation died while the other two survived.

The repair restores observability without weakening any boundary. A new
`test_root_identity_requires_canonical_non_nil_uuid7_without_filename_binding`
exercises the root and parent identities of a child rollout, which carry no
filename residual, over nil, UUIDv1, version-nibble-only, and bad-variant
inputs; `codex-rollout-allows-nil-uuid-identity` now maps to it, since nil
acceptance is observable nowhere else. The session test additionally gains
`019ff8ee-eb1c-4de3-815d-3deea9eca028`, which preserves the exact UUIDv7
timestamp and RFC variant of `_SESSION` and changes only the version nibble, so
the residual check cannot mask a weakened version domain. A probe confirmed the
unmutated source refuses all four inputs while each mutation accepts at least
one, and a positive control confirmed the fixture otherwise attests. The
focused suite passes 279 tests and Ruff lint/format pass.

The confirming rerun then exited zero for `211563c7`: its baseline passed in
200,798 ms, all 151 curated mutations were killed, zero survived or were
invalid, and `source_unchanged=true`. The expanded decision-conformance gate is
therefore satisfied for the current candidate. This is a source and simulation
result only; it advances no Installed or Live matrix layer.

Candidate `e80cb40c`, which repairs the two Rule-8 host negatives, then ran the
same gate and also exited zero: baseline 201,500 ms, 151/151 killed, zero
survived or invalid, and `source_unchanged=true`. The curated mutation that
disables the Hermes evaluated-negative branch remains killed, confirming that
making Agency-blind paths fail open did not weaken the blocking path the
verifier's definite negative depends on.

Candidate `967b0a2c`, which makes the host-parity suite hermetic and proves
Rule 7, also exited zero: baseline 211,811 ms, 151/151 killed, zero survived or
invalid, and `source_unchanged=true`.

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
