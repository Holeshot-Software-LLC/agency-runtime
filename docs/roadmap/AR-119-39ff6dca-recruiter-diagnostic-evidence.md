---
title: "AR-119 no-cost recruiter diagnostic for pair 39ff6dca"
status: active
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [roadmap, evidence, recruiter, staffing, diagnostics, AR-119, AR-252]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - agency_runtime/core/accepted_outcome_canary_contract.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/selector/receipt_projection.py
  - tests/test_workforce_inference.py
  - tests/test_preflight_failure_diagnosis.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 no-cost recruiter diagnostic for pair 39ff6dca

This package records the failed accepted-outcome draw after PR #303 and inspects
the evidence that survived it. The Store was opened read-only, source and
retained host artifacts were searched locally, and the prompt was reconstructed
only where immutable inputs permitted it. No provider, host CLI, canary, config
write, install, push, or hosted workflow ran during this diagnosis.

## Draw identity and terminal boundary

- Exact main: merge `eff66c67a0ff0e23c0ed61d603fa51e8ca23183f`, PR
  [#303](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/303),
  exact PR head `dbfe2b0dd74ed3423cb6fd33f8d49c37e30dd376`.
- Pair: `39ff6dca0e5885d132cefadecc3e1fdb`.
- Run `6af83ef7-559e-4ae0-a654-527c3b266c33`, trace
  `33972524-68b4-4c1a-a4f0-3ca12d8b0ed1`, session
  `bc07c2e2-267c-47be-8df5-929cc7e1436a`.
- Started `2026-08-20T20:44:14.236948Z`; ended
  `2026-08-20T20:45:18.759Z` as `preflight_failed`.
- Failure receipt `bbb028a0-3ddd-44b1-a09f-a9bda230d133` records
  `routing / workforce_inference_failed / runtime_error`.
- The host process exited 0, but the canary wrapper returned red at
  `delivery_marker_absent`. No route, child judge, delegation, specialist or
  skill load, worker run, finalization, accepted outcome, attestation, or
  promotion exists for this trace. No matrix cell moves.

The requested child judge was `codex-subscription`, but parent staffing failed
first. There is therefore no actual answering child provider to report.

## The two rejected recruiter results that survived

The failure receipt retains an allowlisted semantic projection, not model
prose. In order, its actual provider attempts are:

| Stage | Actual provider/model | Status | Retained validation result |
|---|---|---|---|
| planner | `claude-haiku` / `haiku` | applied | `structured_response_applied` |
| recruiter | `codex-subscription` / `gpt-5.6-terra` | rejected | `unit-parseport-impl-verified`; `staff_without_safe_team`; ranked `typescript-application-engineer`, `minimal-change-engineer`, `backend-service-engineer`, `solidity-smart-contract-engineer`; no requirement axis; no top-ranked ineligibility |
| recruiter repair | `codex-subscription` / `gpt-5.6-terra` | rejected | same unit and code; ranked `typescript-application-engineer`, `minimal-change-engineer`; requirement axis `capability`; no top-ranked ineligibility |

This proves a valid planner result followed by two recruiter outputs that each
said `staff`, ranked real roster identities, and nevertheless admitted no
verifier-safe team. It does **not** prove either output's original
`required`/`acceptable`/`forbidden` classifications because those fields were
not retained.

### Raw-response limit

The exact two recruiter JSON bodies are not recoverable after this completed
draw. The Store has no raw workforce-response table, `model_receipts` has zero
rows for the trace, the workforce response cache is process memory only, and
the canary's private cross-provider runtime was deleted when its bounded process
ended. A local trace/pair/unit search found the later diagnostic summaries but
no provider-authored response body. Claiming exact classifications or evidence
strings now would be reconstruction presented as observation, so this package
does not do it.

## Prompt inspection

The parent canary prompt is exactly reconstructable because the pair identity
and source builder are immutable. It is 2,367 characters with SHA-256
`471ebd9249cd00cd55220a004eea67baccbf915a715f70db2e66e7b5cbf920c4`.
The Store's content-capture ceiling retained its exact first 2,000 characters,
SHA-256 `c90d13ca615d169c7da9f45885e8ff948b827dd1d2a9695bd6981fa4a1698da8`;
that value byte-equals the full prompt's 2,000-character prefix.

The byte-exact dynamic recruiter prompt cannot be reconstructed because it
contains the applied planner document and that document was not persisted. Its
source-defined shape is still exact: request, planner document, host context,
authoritative plan/roster bindings, response contract, complete eligible detail
cards, and deterministic typed recall.

Inspection of exact-main source found the unsafe output-contract gap:

1. The primary prompt called `required` “essential” and `acceptable` an
   alternative/complement, but never said that **every required candidate is a
   mandatory selected member** or that acceptable candidates are optional.
2. The response contract exposed the numeric limit and safe-coverage boolean,
   but did not machine-state how selection is derived from the three
   classifications.
3. The repair system referred to a “prior response”, but the repair request was
   the original prompt plus a generic failure row. It did not contain the prior
   classifications, effective required count, actual team-search pool, exact
   missing requirements, complement slots, or candidate coverage relevant to
   the failure.
4. The axis calculation could count coverage from a candidate the recruiter
   itself marked forbidden, even though the team search excludes that candidate.
   That is one possible explanation for an absent axis, not a claim about this
   unrecoverable raw response.

The repair therefore asked the same model to fix an “unsafe team” while
withholding the facts that distinguish overusing `required`, excluding a needed
complement, and genuinely missing typed coverage. The second response's smaller
ranking then lost the `capability` axis.

## Bounded source repair

The local candidate changes the recruiter contract, not routing:

- `required` now explicitly means mandatory and consumes a team slot;
  `acceptable` means an optional alternative/complement; `forbidden` is
  excluded. A `staff` row must admit a subset containing every required member,
  staying within the per-unit limit, and covering every exact requirement.
- The dynamic response contract carries those derivation rules as booleans.
- A rejected safe-team row now receives a prompt-only `safe_team_contract` with
  the effective required/team-search sets, available complement slots, exact
  uncovered requirements, and bounded ranked-candidate coverage/classification
  facts. It includes no model prose and no deterministic replacement team.
- Durable failure receipts add only the three content-free integers proposed in
  the earlier AR-253 diagnosis: effective required count, ranked executable
  count, and `maximum_selected_per_unit`. Legacy receipt strings remain valid.
- Axis diagnosis excludes model-declared forbidden candidates. Deterministic
  code still only rejects and explains; it never adds, reorders, selects, or
  converts an invalid response into a contractor gap.

Provider order, parent-recruiter pinning, child-judge pinning, canary prompts,
owner config, and ordinary-turn routing are unchanged.

## Provider-free verification and next live boundary

The focused recruiter, preflight-receipt, and decision-conformance suites pass
**97/97** with warnings as errors. They reproduce semantic-forbidden coverage,
required-slot starvation (`required=4`, executable=5, maximum=4), roster-wide
uncovered capability, count round-tripping, malformed-count rejection, one
bounded repair, and the invariant that repair feedback never supplies a
selected team. The warning-strict production spine also passes 797 tests with
20 skips, and the deterministic AR-119 matrix regression suite passes 695/695.
Those tests do not create live evidence or move a matrix cell.

This is source/diagnostic evidence only. Before any further live draw, the
candidate still needs its exact-commit local gate harness, recovery commits, review,
authorized publication, exact-main installation, and a fresh explicit
one-draw authorization. A future green draw would be new evidence; this package
does not retroactively turn pair `39ff6dca…` green or move any rule or matrix
cell.
