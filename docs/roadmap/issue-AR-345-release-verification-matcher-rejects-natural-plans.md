---
title: "AR-345: Release-verification plan matcher rejects natural planner phrasing, forcing fail-open turns"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, planner, plan-policy, fail-open, reliability]
related:
  - docs/roadmap/issue-AR-344-codex-fail-open-stop-terminal-exit.md
  - docs/roadmap/issue-AR-346-hermes-fail-open-draft-replacement.md
  - docs/roadmap/issue-AR-335-make-content-invalid-completions-reach-fallback.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-345
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/402
depends_on: []
blocks: []
---

# AR-345: Release-verification plan matcher rejects natural planner phrasing, forcing fail-open turns

## Problem

Any release-shaped request (a request whose tokens intersect `_RELEASE`:
install/deploy/release/ship and inflections) deterministically fails
workforce inference on every host. `plan_policy_violations` adds
`plan_missing_release_verification` unless some test-evidence unit's
outcome passes `_outcome_verifies_operation`
(`agency_runtime/core/workforce/plan_policy.py:397-412`), which requires
a `_POSITIVE_VERIFICATION` token within 8 tokens of an operation token
with **every intervening token drawn from a 21-word filler list**
(`_VERIFICATION_RELATION_FILLERS`, lines 142-166). Any ordinary noun in
between — "plugin", "gateway", "battery" — breaks the match.

Measured against the matcher directly (installation vocabulary),
natural release-verification outcomes fail 6/10:

| passes | outcome sentence |
|---|---|
| yes | "Verify the installation succeeded" |
| yes | "Confirm the installed plugin loads in the gateway after restart" |
| no | "Test evidence confirming the plugin is correctly installed and loaded" |
| no | "Run the harness battery and confirm the reinstalled plugin passes" |
| no | "Confirm the plugin installation completed and the gateway loads it" |
| yes | "Verify that the install completed successfully" |
| no | "Verify the plugin was installed" |
| yes | "Independently verify successful installation of the openclaw plugin" |
| no | "Test evidence verifying the installation and gateway load of the plugin" |
| no | "Verify gateway restart and confirm plugin registration is active" |

("Verify the plugin was installed" fails because "plugin" is not a
filler token.) The planner repair guidance
(`plan_missing_release_verification` in `_PLAN_REPAIR_REQUIREMENTS`)
says only "Add downstream test-evidence whose outcome explicitly
verifies the requested install, deployment, or release" — it never
states the lexical-adjacency contract, so repair attempts fail the same
way. "reinstall"/"reinstalled" are also absent from the `_RELEASE`
vocabulary while "installed" matches, so a reinstall request is
release-shaped but its natural echo in the plan is not.

## Measured 2026-09-01 (runtime e5e2e193, cloud planners)

A live diagnostic preflight (host hermes, session
`diag-ar341-followup-20260901`, message "Repair the openclaw native
plugin registration: reinstall …, verify …, and confirm the installed
plugin passes its harness battery") failed 4/4 planner attempts across
three cloud models (glm-5-turbo, gpt-5.5, fallback gpt-5.6-terra), all
`provider_response_contract_invalid` with
`plan_missing_release_verification` in every attempt, ending in
`workforce_inference_failed ["inference_invalid"]`. The same signature
appears in hermes turns 776/777 of session `20260901_100009_f7574e`
(the AR-346 trigger) and in the deliberate codex reproduction for
AR-344. Non-release-shaped requests staffed normally in the same window
(codex acceptances at confidence 1.0, 13:56-13:58Z), so this is a
deterministic subset of — not the whole of — the intermittent
staffing-verdict window documented in the AR-338 capsule.

## Impact

Every install/deploy/release-flavored turn runs Agency-blind, which is
exactly the population that then hits the fail-open finalization
defects: the codex Stop terminal replay-mismatch (AR-344) and the
hermes draft replacement (AR-346). An agency-runtime operations session
(install, wire, battery) is release-shaped almost every turn.

## Acceptance

- [ ] A plan whose test-evidence outcome verifies the requested
      operation in natural phrasing (including the 6 failing rows
      above) passes `_release_verification_covers_request`, without
      admitting negated or unrelated-verification outcomes.
- [ ] `reinstall`/`reinstalled`/`reinstalling` count as installation
      vocabulary on both the request and outcome sides.
- [ ] Planner repair guidance states the actual acceptance contract for
      release verification so a rejected plan can be repaired in one
      pass.
- [ ] Regression coverage pins the sentence table above.
