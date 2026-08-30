---
title: "AR-331: Align plan-policy discovery inventory with the deterministic planning oracle"
status: done
category: roadmap
created: 2026-08-29
updated: 2026-08-30
tags: [bug, workforce, plan-policy, planning, evals]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - agency_runtime/core/workforce/plan_policy.py
  - agency_runtime/core/workforce/fallback.py
  - tests/test_workforce_inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-331
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/345
depends_on: []
blocks: []
---

# AR-331: Align plan-policy discovery inventory with the deterministic planning oracle

## Problem

`plan_policy._PlanInventory.discoveries` admits only units whose
`artifact_kind` is `analysis`, while `fallback.deterministic_work_plan` emits
its own `unit-codebase-discovery` as `review-report` with the `discovery`
lifecycle. For repository-security review and audit requests the oracle's own
plan is therefore rejected by the policy it is supposed to model, with
`plan_missing_codebase_discovery`.

## Current state

- Reproduced on 2026-08-29 against the installed `755efedc` production venv:
  "Review authentication security in this repository code.", "Audit the
  security of the authentication code in this repo.", and "Fix the
  authentication security bug in this repository and verify the fix." each
  produce a deterministic plan that fails `plan_policy_violations` with
  `plan_missing_codebase_discovery`.
- Production turns are unaffected: turn planning is inference-only and
  `deterministic_plan_and_staff` is consumed only by the decision-conformance
  evaluation. The defect predates the AR-297 policy correction `687386f6`,
  whose `analysis`-kind filter is unchanged from the prior policy.
- No named gate exercises `plan_policy_violations` over the deterministic
  oracle's repository-security outputs, which is why two independent review
  passes missed the disagreement.
- The `plan_missing_codebase_discovery` repair guidance still names only a
  "software-engineering analysis unit" although the corrected policy admits
  the built-in `codebase-discovery` domain as well.
- Resolved 2026-08-30: the policy inventory admits read-only `review-report`
  discovery units alongside `analysis`, the oracle emits the same
  `unit-codebase-discovery` predecessor for security-typed repository
  mutations (the third reproduced request previously planned no discovery
  unit at all), and the repair guidance names both admitted built-in
  repository-analysis domains. A focused test proves all three reproduced
  request shapes pass `plan_policy_violations`, a companion test proves the
  widened inventory still rejects non-repository review-report units, and
  the decision-conformance mutation evaluation passes 167/167 with the
  aligned shape.

## Approach

Choose the canonical discovery-unit shape once: either the oracle emits its
codebase-discovery unit as a read-only `analysis` artifact in the `discovery`
lifecycle, or the policy inventory admits `review-report` discovery units.
Align both sides, extend `tests/test_workforce_inference.py` to run
`plan_policy_violations` over deterministic oracle outputs for the
repository-security request class, and refresh the repair-guidance text to
name both admitted repository-analysis domains.

## Dependencies

None. Coordinate with the decision-conformance baseline so the aligned shape
does not silently change recorded conformance outcomes.

## Acceptance

- [x] The deterministic oracle's repository-security plans pass the installed
      plan policy.
- [x] A focused test runs the policy over deterministic oracle outputs for the
      three reproduced request shapes.
- [x] The `plan_missing_codebase_discovery` repair guidance names both
      admitted built-in repository-analysis domains.
- [x] Focused workforce-inference tests pass warning-strict.
