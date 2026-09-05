---
title: "AR-386: The strict critic vetoes every verifier-accepted install turn"
status: done
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, critic, staffing, inference, receipts]
related:
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-306-bind-strict-critic-semantics.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-386
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/643
depends_on: []
blocks: []
---

# AR-386: The strict critic vetoes every verifier-accepted install turn

## Problem

Once AR-384 let the verifier accept a `staff` decision on an install-flavoured
plan, the strict critic became the gate, and it closed every time.

Measured 2026-09-03 on nine fresh install-flavoured preflight turns through
the AR-384 branch runtime, installed `workforce.mode: strict`, critic served by
one deployment (`x-litellm-model-id 10729e08-a962-5f82-bcf0-1b35b4adcf47`):

| turn | request | verifier | critic verdict |
|---|---|---|---|
| 203 | make the helix editor usable from my terminal | accepted; `unit-install-plan` staffed `operations-manager` | `wrong-neighbor-selection`, `missing-implementation-lifecycle-assurance` |
| 204 | set up the Zed editor | accepted; install plan staffed `operations-manager` + `sre-site-reliability-engineer` | `verification-evidence-worker-misfit` |
| 205 | install ripgrep and fd | accepted after one repair | `selected-team-lacks-live-installation-authority` |
| 209 | put helix on this computer | accepted after one retry | `planner-domain-mismatch`, `test-authoring-mismatch`, `visual-evidence-mismatch` |

Four of four verifier-accepted install turns ended `staffing_critic_rejected`
and `no_specialist_fail_open`. The other five turns never reached the critic
(AR-385 truncation, AR-373 charset, or a coverable `domain:platform` token).

Two of the codes are the critic doing its job: `wrong-neighbor-selection` on
turn 203 names `api-platform-engineer` staffed onto a helix install unit, and
`planner-domain-mismatch` on turn 209 names the planner's `platform` domain
colliding with the roster's API-platform meaning (AR-384 residue). Two are
not:

- `selected-team-lacks-live-installation-authority` demands execution
  authority from an advisory workforce. Agency supplies expertise; the host
  executes. No contract can hold live installation authority, so the code can
  never be satisfied and vetoes every install turn by construction.
- `missing-implementation-lifecycle-assurance` on a plan that has no
  implementation unit asks for assurance of mutation work the planner did not
  plan, because a plan-authority install unit is the honest shape when Agency
  cannot mutate the machine (AR-374).

The critic document carries `verified_staffing` including the new
`roster_coverage_gap` reasons and `critic_contract.verified_staffing_hard_checks_passed`,
but nothing that says the workforce is advisory, that waived gaps are runtime
facts rather than defects, or that a plan-only install is a legitimate shape.

## Current state

**Implemented on branch `claude/ar386-critic-contract` (2026-09-03)** per
[ADR-0200](../decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md).
`critic_contract` now states `workforce_is_advisory`,
`execution_authority_holder: host`, `selected_authority_bound_by_eligibility`,
`roster_coverage_gaps_are_runtime_waivers` and
`plan_authority_units_for_host_side_work_are_intended`, and lists
`veto_grounds` and `never_veto_for`; `_CRITIC_SYSTEM` says the same in words
and narrows the lifecycle ground to assurance the plan calls for. On a veto
the staffing decision carries each critic code as `critic_<code>` (hyphens
folded, at most sixteen, at most 56 characters) beside
`staffing_critic_rejected`, so `staffing_reason_codes` on the preflight-failure
receipt, `global_reason_codes` on the routing receipt and the fail-open
disclosure line all name the veto. `tests/test_strict_critic_doctrine.py`
pins the contract and two curated decision-conformance mutations guard it.

Live re-measurement, the nine wordings above plus AR-385's two install
wordings, branch runtime, installed `workforce.mode: strict`, critic served by
the same deployment as before (evidence in
`docs/roadmap/acceptance/evidence/AR-386-evidence-20260903.txt`):

| turn | reached the critic | verdict | outcome |
|---|---|---|---|
| 201, 202, 206, 207 | no | - | recruiter or verifier: AR-384 and AR-373 residue |
| 203 | no | - | recruiter declared a gap; hiring ran, no hire landed |
| 204, 205, 208, 305 | yes | `wrong-neighbor-selection` | `staffing_critic_rejected`, receipt `['staffing_critic_rejected', 'critic_wrong_neighbor_selection']` |
| **209** | yes | approved | **accepted**: six specialists staffed |
| **304** (fresh wording, vetoed under the old prompt this morning) | yes | approved | **accepted**: four specialists staffed |

Two install turns completed with a staffed team under strict mode. Four
vetoes, each on the one fair ground the contract names; the two
doctrine-breaking codes of the AR-384 measurement did not recur, and no veto
carried an execution-authority code. The turns that never reached the critic
are AR-384's `domain:platform` residue, AR-373's row-shape residue, and one
gap that hiring did not fill; none is this issue.

The critic document previously carried `verified_staffing` including the
`roster_coverage_gap` reasons but nothing that said the workforce is
advisory; AR-306 had bound the critic to the configured thresholds and
selected-only composition only.

**Verification (2026-09-03).** The acceptance record is frozen at
`6b79736c`; the isolated codex verifier returned satisfied on all three
criteria (runs `AR-386.1-20260903-c6a70036`, `AR-386.2-20260903-e29d950c`,
`AR-386.3-20260903-95476868`), so the issue is done. Under the ADR-0201
runtime the same eleven wordings produced two vetoes (208, 209), both
`wrong-neighbor-selection`, neither on a platform-domain selection.

## Approach

1. State the advisory doctrine in the critic contract and system prompt:
   Agency never executes, the host does; a selected team's authority is bound
   by eligibility already; `roster_coverage_gap` entries are runtime waivers,
   not team defects; a plan-authority unit for host-side work is the intended
   shape. Keep the veto for wrong neighbours, lifecycle assurance the plan
   actually calls for, unsafe composition and unsupported confidence.
2. Record the critic's codes on the routing receipt beside the verifier's,
   bounded and closed, so a veto is diagnosable without the capture harness.
3. Re-measure the same nine wordings. Acceptance is at least one install turn
   completing with a staffed team, and no veto carrying an execution-authority
   code.

Not proposed: dropping the critic in strict mode, auto-approving on any code,
or changing the critic route.

## Dependencies

- AR-384 made the verifier accept these turns; its `domain:platform` residue
  is what the critic's `planner-domain-mismatch` names.
- AR-374 explains why install work is planned as plan-authority units.
- AR-306 and AR-304 own the critic contract and its diagnostics.

## Acceptance

- [x] The critic contract and system prompt state that the workforce is
      advisory, that waived coverage gaps are runtime facts, and that a
      plan-authority unit for host-side work is a legitimate shape.
- [x] A fresh-wording helix install turn completes with a staffed team under
      `workforce.mode: strict`.
- [x] No strict-critic veto on the nine 2026-09-03 wordings carries an
      execution-authority code.
