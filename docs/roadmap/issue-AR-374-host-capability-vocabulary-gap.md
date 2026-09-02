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

The drift guard in Acceptance 4 is landed. The remaining decision is which of
these to take, and that is an owner call because they have different blast
radii:

- **Validate the planner's `required_tools` against the host context** and
  fail or repair explicitly, so an out-of-floor tool never becomes a silent
  roster-shaped abstention. Smallest change; fixes the misleading receipt.
- **Collapse the tool-class vocabulary** to what a host can prove, moving
  specialism terms onto an axis that is not an eligibility gate. Largest
  change; addresses hypothesis 3 at the root and unblocks the eval.
- **Feed real capability detection** into `available_tools` so the union path
  stops being inert. Addresses hypothesis 2 and is the only option that makes
  a browser-requiring card genuinely staffable.

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
      cleared on a real host context, and the residual blocker is a recruiter
      provider failure, not eligibility. It needs its own issue.
- [x] Whatever the fix, a regression test pins that the capabilities a host
      proves and the tool classes the roster demands cannot silently drift
      apart again. `tests/test_host_capability_vocabulary_drift.py` with
      `tests/data/ar374_capability_vocabulary_baseline.json`; both drift
      directions were proven to fail the guard.

## Follow-ups

Two defects were found while establishing the above and are not in this
issue's scope. Neither has an internal ID or tracker row yet; both need
owner authorization before an outward-facing tracker write.

1. **Unvalidated planner `required_tools`.** The planner is instructed to
   draw `required_tools` from `host_context.available_tools` and nothing
   enforces it. One out-of-floor value makes a unit unstaffable by the whole
   roster and reports it as `agent_tools_missing`.
2. **The upstream selection eval cannot reach 82 percent of the roster.** It
   filters candidates on `contract.tool_classes` against the host's nine
   (`core/evals/upstream_selection.py:604`), a gate the staffing path
   deliberately does not apply, so the eval scores a roster far smaller than
   the one production selects from.
