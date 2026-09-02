---
title: "AR-374: Most of the roster is permanently ineligible because hosts prove 9 capabilities and the roster demands 246"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, eligibility, host-capabilities, staffing]
related:
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-374
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/540
depends_on: []
blocks: []
---

# AR-374: Most of the roster is permanently ineligible because hosts prove 9 capabilities and the roster demands 246

## Problem

`_NATIVE_HOST_CAPABILITIES` (`core/host_capabilities.py:325`) grants every
execution host the same fixed nine capabilities:

    code-execution, native-delegation, package-management, repository-read,
    repository-write, runtime-evidence, shell-execution, source-control,
    test-execution

The governed roster demands **246 distinct tool classes**. Measured
2026-09-02 against the shipped 291-worker index:

| | count |
|---|---|
| workers eligible on tools | 72 |
| workers requiring a capability no host can prove | **219 (75%)** |

Top blockers: `browser-interaction` (55 workers), `web-research` (43),
`analytics-reader` (27), `database-access` (19), `current-legal-research`
(13), `spreadsheet-access` (12), `monitoring-observability` (11),
`crm-reader` (11).

The title's claim that those 219 are therefore unstaffable is **wrong**, and
the correction is recorded under Findings below. The vocabulary gap is real;
its consequence is not the one this issue was filed with.

## Current state

Investigated 2026-09-02. The measurement reproduces exactly, from both the
live 291-worker store and the bundled 265-card manifest. What does not hold
is the inference drawn from it.

### The measured gap (acceptance 1)

Every execution host proves the identical floor, so the share is the same for
all five. Against the bundled manifest (`core/roster/data/manifest.json`):

| host | proven | cards demanding an unprovable class | distinct blockers |
|---|---|---|---|
| codex | 9 | 218 / 265 (82%) | 238 |
| claude | 9 | 218 / 265 (82%) | 238 |
| openclaw | 9 | 218 / 265 (82%) | 238 |
| hermes | 9 | 218 / 265 (82%) | 238 |
| zcode | 9 | 218 / 265 (82%) | 238 |

Against the live store, which also holds locally hired workers, the same
measurement is 219 / 291 (75%). Of the 246 distinct classes the roster
demands, **238 (97%) cannot be proven by any host**. Only 8 of the 9 proven
capabilities are demanded by any card at all; `native-delegation` is demanded
by none.

### The correction: this gap does not gate production staffing

`agent_tools_missing` is raised in `staffing_verifier._eligibility` by

    required_tools = set(unit.required_tools)
    if not required_tools <= context.available_tools:

The comparison is between the **work unit's** required tools and the host's
proven tools. It never reads `contract.tool_classes`; the code says so
directly, and the surrounding comment records that re-gating contracts on
their declared tools was removed deliberately as "the legacy
broad-required-tool trap".

Measured against the 219 blocked workers, with a unit that requires no tools
and a host proving the nine:

- **0 of 219** raise `agent_tools_missing`.
- A worker declaring `browser-interaction`, `web-research`,
  `accessibility-tester` and `assistive-technology-test-host`
  (`section-508-accessibility-specialist`) returns an empty ineligibility
  tuple: fully eligible.
- A worker declaring **no** tool classes at all (`meeting-notes-specialist`)
  *is* rejected with `agent_tools_missing` when the unit demands `ci-runner`.

Eligibility on this axis is a property of the unit, not of the worker. The
only contract-scoped tool gate in the tree is
`core/evals/upstream_selection.py:604`, which filters on
`contract.tool_classes`. That is the eval harness, not the staffing path.

### The reproduction over-constrained the host

The capsule's repro passes `frozenset({"native-delegation",
"repository-read", "shell-execution"})` — three tools. A real host proves
nine. The omitted `test-execution` is exactly the capability the planner
asks for, so the probe manufactured the failure it then measured.

Re-run with the real nine, for the same `install this: https://zcode.z.ai/en`
request, the planner produced three units requiring only `repository-read`
and `test-execution` — every one inside the floor, no `agent_tools_missing`
anywhere. The blocker observed on that run was instead the recruiter
returning `provider_no_valid_response`, and on an earlier run
`provider_response_contract_invalid`, with the AR-373 fix confirmed present
in the installed venv.

### Hypotheses (acceptance 2)

1. **The roster over-declares — rejected as a cause.** Over-declaration may
   well exist, but it produces no ineligibility in the staffing path, so it
   cannot be what abstained the turn. It does constrain the upstream
   selection eval, which is a real but separate problem.
2. **The host under-declares — confirmed as mechanism, and it is inert.**
   `native_adapter_capability_receipt` unions adapter-reported tools onto the
   floor (`core/host_capabilities.py:776`), so the nine are a floor, not a
   ceiling. But every production caller omits `available_tools`:
   `adapters/base.py:903`, `core/native_child_staffing.py:992`, and
   `core/chaos/experiments.py:303`. No capability detection exists anywhere
   in the tree. The extension path is real and never fed.
3. **The vocabulary is mis-scaled — confirmed, and the strongest of the
   three.** 238 of 246 demanded classes are unprovable by any host and one
   proven capability is demanded by nobody. An axis with 97 percent
   unprovable terms is describing specialisms, not host facilities.

### Why the receipt misleads

`_PLANNER_SYSTEM` instructs the planner to "Use only exact values from
host_context.available_tools for required_tools". Nothing enforces it:
`required_tools` is shape-validated as an identifier array
(`planning_contracts.py:315`) and never checked against the host context.
When a planner does emit a tool outside the floor, the unit-scoped gate fails
it against *every* worker at once, staffing abstains
`no_safe_sufficient_team`, and the receipt reports `agent_tools_missing` —
which reads as a roster problem and is what sent this issue after the roster.

## Approach

Owner chose the first option: validate the planner's `required_tools` against
the host floor. Landed.

`plan_policy_violations` now takes the host's proven tools and raises
`plan_unit_required_tools_unproven` when any unit demands one the host has not
proven. The code is registered through `_PLAN_REPAIR_REQUIREMENTS`, so the
existing planner repair loop feeds it back with a named correction and the
planner gets one bounded chance to author a plan this host can staff. It is
wired at both call sites: parse time, which is what reaches the repair loop,
and the post-staffing check, which is the only place a cache-replayed plan is
re-checked against this turn's host.

The rule is deliberately topology-independent — an explicit one-unit plan is
held to it too — and deliberately inert when the host proved nothing, because
an empty proven set means the host proved nothing rather than that it can do
nothing. That case still fails at the downstream staffing gate.

Live evidence, worktree code against the real installation:

- With the capsule's three-tool context, where the planner asks for
  `test-execution`, the plan is now rejected as
  `plan_unit_required_tools_unproven` and repaired once. The planner did not
  recover, so the turn still fails — but it fails naming the plan, not the
  roster. That is the whole point of the change.
- With the real nine, the planner is applied unchanged, the recruiter is
  applied, and the turn now reaches the critic. No regression on the path a
  real host takes.

The other two options are untouched and remain open: collapsing the tool-class
vocabulary to what a host can prove, and feeding real capability detection into
`available_tools`.

## Dependencies

- AR-373 removed the contract failure that masked this; the recruiter now
  reaches a real judgement, which is what made this visible.

## Acceptance

- [x] The share of the roster that is structurally unstaffable is stated,
      per host, with the tool classes responsible. Recorded above: identical
      for all five hosts, 218/265 bundled and 219/291 live, 238 responsible
      classes.
- [x] Each of the three hypotheses above is confirmed or rejected against
      evidence, not assumed. Recorded above: (1) rejected as a cause,
      (2) confirmed and inert, (3) confirmed and dominant.
- [ ] An ordinary install request staffs a specialist on this installation,
      or the reason it should not is recorded. Partially: the tools axis is
      cleared on a real host context and the turn now reaches the critic,
      which rejects the staffing with `missing-installation-executor`,
      `wrong-routine-installation-staffing` and
      `missing-implementation-lifecycle`. That is a planner-shape defect, not
      an eligibility one, and it needs its own issue.
- [x] Whatever the fix, a regression test pins that the capabilities a host
      proves and the tool classes the roster demands cannot silently drift
      apart again. `tests/test_host_capability_vocabulary_drift.py` with
      `tests/data/ar374_capability_vocabulary_baseline.json`; both drift
      directions were proven to fail the guard.

## Follow-ups

Found while establishing the above and out of this issue's scope. None has an
internal ID or tracker row yet; each needs owner authorization before an
outward-facing tracker write.

1. **The upstream selection eval cannot reach 82 percent of the roster.** It
   filters candidates on `contract.tool_classes` against the host's nine
   (`core/evals/upstream_selection.py:604`), a gate the staffing path
   deliberately does not apply, so the eval scores a roster far smaller than
   the one production selects from.
2. **The planner writes no executor for an install request.** With the real
   nine, the install request planned advise, plan and review units and no
   unit with modify authority. The critic correctly rejected the staffing
   with `missing-installation-executor`,
   `wrong-routine-installation-staffing` and
   `missing-implementation-lifecycle`. This is now the live blocker for an
   ordinary install turn.
3. **The recruiter fails intermittently at the provider.** Observed
   `provider_no_valid_response` on one run and
   `provider_response_contract_invalid` on another for the same request, with
   the AR-373 fix confirmed present. A third run succeeded, so it is a
   flake rather than a contract defect.
4. **The decision-conformance eval cannot run on this box as documented.** It
   resolves `sys.executable` through symlinks and runs its baseline isolated,
   so a symlinked venv lands on the system interpreter, which cannot see
   user-site `pytest`. The same failure reproduces on a clean `main`
   checkout, so it is environmental. A `venv --copies` with the user site
   added by `.pth` runs it correctly.
