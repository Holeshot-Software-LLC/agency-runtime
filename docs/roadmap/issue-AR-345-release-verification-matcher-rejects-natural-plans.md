---
title: "AR-345: Release-verification plan matcher rejects natural planner phrasing, forcing fail-open turns"
status: done
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

## Resolution (2026-09-01)

`_outcome_verifies_operation` now accepts a clause that contains both a
verification token and an operation token, dropping the filler-only
adjacency window; negation stripping and the clause boundaries
(punctuation plus temporal words) are unchanged, so negated outcomes
("Does not verify the installation", "…without installing anything")
and temporally-scoped ones ("Verify the test results before
installation") still fail, as do outcomes that never name the
operation. One correction to the measured table: row 10 ("Verify
gateway restart and confirm plugin registration is active") contains
no installation token and is correctly rejected under any sound rule —
9 of 10 rows pass, the 6 previously-failing natural phrasings among
them. `reinstall*` joins the release and installation vocabularies on
both sides, `-ing` verification forms (verifying/confirming/validating/
proving) are recognized, and the repair guidance plus the planner
acceptance contract now state the clause rule with an example so a
rejected plan repairs in one pass. Note: fail-open turns stop only
after a runtime deploy at a commit containing this fix (venv rebuild +
`agency install`, per the standing deploy runbook).

## Review round (2026-09-01, PR #412)

The PR's code review reproduced nine follow-on defects; all confirmed
ones are fixed in-branch:

- The deterministic fallback planner kept a divergent `_RELEASE` copy
  without `reinstall*`, so its own plan for a reinstall code-mutation
  request violated the policy that judges it — the AR-345 failure mode
  through the untouched path. `fallback._RELEASE` now sources
  `RELEASE_OPERATION_TOKENS` (itself derived as the union of the
  per-operation vocabularies, killing the third hand-kept copy), plus
  its fallback-only `package` extra, with a parity + end-to-end
  regression test.
- Third-person verification forms (`verifies`/`confirms`/`validates`/
  `proves`/`tests`/`testing`) are recognized; `uninstall*` joins the
  installation vocabulary for symmetry.
- Clause-boundary semantics corrected: `then` now splits (an outcome
  that merely performs the operation next no longer counts as
  verification) while `after`/`following`/`once` no longer split —
  verifying behavior after the install/deploy IS release evidence.
- Negated scopes stop at commas ("Without manual steps, confirm the
  installation succeeds" passes) and recognize "nothing" ("Verify
  nothing was installed" fails).
- The reinstall round-trip test was vacuous (its request carried no
  mutation/code token so the gate never evaluated); it now uses a
  code-mutation request and pins both arms.

Known accepted tradeoff (review finding, unfixed by design): within a
clause the match is bag-of-words, so an outcome that verifies something
unrelated while mentioning an operation word can over-satisfy the gate;
the gate's job is forcing plans to include release evidence, and
over-demanding was the epidemic.

## Acceptance

- [x] A plan whose test-evidence outcome verifies the requested
      operation in natural phrasing passes
      `_release_verification_covers_request`, without admitting
      negated, temporally-scoped, or unrelated-verification outcomes
      (9/10 measured rows pass; row 10 never names the operation and
      is correctly rejected — see Resolution).
- [x] `reinstall`/`reinstalled`/`reinstalling` count as installation
      vocabulary on both the request and outcome sides.
- [x] Planner repair guidance states the actual acceptance contract for
      release verification so a rejected plan can be repaired in one
      pass.
- [x] Regression coverage pins the sentence table above
      (`tests/test_workforce_intent.py::test_natural_release_verification_phrasings_match_the_operation`
      plus the reinstall request/outcome round-trip).
