---
title: "AR-343: Reject explicitly empty artifact_kinds instead of granting wildcard coverage"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, staffing, validation, hardening]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/issue-AR-342-codex-activation-canary-route-unsatisfiable.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-343
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/398
depends_on: []
blocks: []
---

# AR-343: Reject explicitly empty artifact_kinds instead of granting wildcard coverage

## Problem

`_artifact_kinds` (`agency_runtime/core/workforce/contract.py:257-258`)
returns the explicit value verbatim whenever the `artifact_kinds` key is
present, before the derivation branch whose terminal
`if not result: result.append("analysis")` guarantees a non-empty tuple.
An explicit `artifact_kinds: []` (or `null`) therefore produces `()`,
and `typed_covered_requirements`
(`agency_runtime/core/workforce/staffing_verifier.py:461-464`) reads a
contract with no typed fields as a **wildcard that covers every
requirement**. The wildcard fallback is deliberate for un-enriched
roster contracts (`is_wildcard_coverage` documents it as
`untyped_candidate` presentation), but it makes an author's positive
declaration "this worker produces no artifacts" indistinguishable from
"this contract was never enriched" — a validation hole that reads as
permissive staffing rather than as a rejection.

Two secondary weaknesses in the same explicit branch, same source:
identifier *shape* is validated but the `ARTIFACT_CAPABILITY`
vocabulary is not, so a plausible model-authored kind (e.g.
`design-doc`) survives the contract, is silently dropped from
`capability_ids`, can never match a unit's artifact axis, yet still
marks the contract non-wildcard; and `implementation-change` is the only
derivation rule requiring both archetype and task type while
writer/tester/architect trigger on archetype alone (measured benign on
the current roster: all 82 implementers carry the task type).

## Reachability

Not reachable through shipped producers today. The bundled manifest
supplies zero explicit `artifact_kinds` (263 agents checked), and both
producers (`hiring.py` and `known_installer.py` in
`agency_runtime/core/workforce/`) derive `artifact_kinds` and
`task_types` from the same `artifacts` tuple, where an empty tuple makes
`normalize_capability_ids` raise before a contract exists — though that
is a second field's guard firing with a misleading message, not this
function's own validation. This is hardening for the first producer or
sync path that hands the field through directly.

## Provenance

Found by an Agency-staffed `code-reviewer` turn (claude host, routing
accepted at confidence 1.0, trace `23315857-…`) during the 2026-09-01
Windows live-header demo on runtime `ec6c4b49`; claims verified against
source before filing.

## Resolution (2026-09-01, this PR)

`_artifact_kinds` rejects explicit empty/null declarations and explicit
sets with no `ARTIFACT_CAPABILITY` member; underscore alias spellings of
ontology kinds normalize instead of rejecting. Mixed sets deliberately
keep model-authored members: dynamic hiring merges the causing unit's
ontology kind with novel `artifacts_produced` names (`hiring.py`), and
full out-of-vocabulary rejection measurably breaks hire compilation
(`test_workforce_dynamic_hiring.py::test_hire_compiles_schema_maximum_lists`),
so "no vocabulary member at all" is the strictest rule that does not
regress live hires — that is the never-matching hazard this issue names.
The strict checks guard fresh authorship only: `parse_workforce_contract`
re-derives degenerate stored legacy rows so one historical row cannot
fail every roster read, index snapshot, self-heal reconciliation, or
sync (review finding on PR #401). The sibling axes hole
(explicit-empty `stacks`/`lifecycle_phases`/`domains`) is filed
separately as AR-351.

## Acceptance

- [x] An explicitly empty or null `artifact_kinds` value is rejected at
      contract validation (or documented-and-normalized to derivation),
      and can no longer produce wildcard coverage.
      (`contract.py::_artifact_kinds`;
      `test_explicitly_empty_artifact_kinds_is_rejected_not_wildcarded`.)
- [x] Explicit artifact kinds with no `ARTIFACT_CAPABILITY` member fail
      validation instead of silently never matching; mixed sets keep
      their novel members (see Resolution — full rejection breaks
      shipped dynamic hiring), and alias spellings normalize.
      (`test_explicit_artifact_kinds_need_at_least_one_vocabulary_member`,
      `test_underscore_alias_spellings_of_ontology_kinds_are_normalized`.)
- [x] A regression test covers both paths, including the
      `staffing_verifier` wildcard boundary and the stored-contract
      round-trip.
      (`test_wildcard_coverage_is_reserved_for_truly_untyped_contracts`,
      `test_stored_legacy_degenerate_artifact_kinds_stay_parseable`.)
