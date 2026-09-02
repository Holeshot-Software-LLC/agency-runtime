---
title: "AR-357: State the response contract once per turn instead of via superseding snapshots"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [finalization, header-contract, hooks, claude]
related:
  - docs/roadmap/issue-AR-344-codex-fail-open-stop-terminal-exit.md
  - docs/roadmap/issue-AR-366-openclaw-fail-open-withhold.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-357
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/427
depends_on: []
blocks: []
---

# AR-357: State the response contract once per turn instead of via superseding snapshots

## Problem

What a parent must emit to finalize a turn arrives as a stream of
superseding per-tool-observation header snapshots plus an implicit
finalization contract, and the two can drift within one turn. Measured
2026-09-01 on the claude host: a substantive final response that
followed the latest snapshot verbatim was withheld with
`response_invalid, missing: ["evidence_verification"]` (16:12:05Z,
trace `9ff53c55-…`), while adjacent turns using the same pattern were
accepted — the operator lost the turn's summary and the model cannot
tell which requirement it missed.

## Current state

Failure receipt captured; not yet root-caused. The turn-scoped
expectation lives in N superseding snapshots; the finalization
verifier's actual requirement set is not stated anywhere the model can
read it.

Second measured case (2026-09-01 evening, same session): a turn in
which no header snapshot was delivered at all — the model reused the
latest prior-turn snapshot verbatim, and the final response was
withheld with "did not satisfy the exact current-turn evidence header
contract. The turn is terminal; no correction was requested or
accepted." The operator lost that turn's summary and re-asked the
question. This adds the no-snapshot-delivered shape to the defect: the
contract can demand a snapshot the turn never provided.

## Approach

Investigate the claude-adapter verifier first (the miss may be
adapter-side rather than contract-side). Then deliver one canonical
statement of the finalization requirements per turn — in the same
delivery as the kernel or as the single authoritative snapshot — and
make later snapshots strictly additive observations, never a second
contract. A rejected response's `missing` list should name
requirements the model was actually told about.

## Dependencies

- The AR-344 answers (terminal-lifecycle vs bound-response conflation)
  as prior art on this surface.

## Implementation (2026-09-02)

Root cause of the 2026-09-01 withheld response: `missing:
["evidence_verification"]` was never a requirement the model could satisfy.
It is the verifier's own code for "Agency could not read this turn's
evidence" -- in that turn, an unreadable specialist-activation projection.
The finalizer returned it as if it were an unmet header field, and the Stop
path rejected the turn on it. That is precisely the fault rule 8 says Agency
must absorb, so the response should have published unverified.

- `agency_runtime/core/header/response_contract.py` (new) owns the single
  canonical `[AGENCY RESPONSE CONTRACT v1]` statement. Every sentence in it
  is a claim about `validate_completion_policy`, and the text is hash-pinned
  by `tests/test_response_contract.py` so it cannot drift silently.
- The contract is delivered once per turn beside the turn's first values:
  `adapters/hooks.py` (codex/claude/zcode `UserPromptSubmit`),
  `adapters/hermes/bridge.py`, and `adapters/openclaw/node_bridge.py`
  (INITIAL only). Refreshed snapshots carry `SNAPSHOT_VALUES_ONLY_NOTE` and
  no requirement text, so no snapshot can read as a second contract; the
  openclaw refresh path renders `UPDATED` directly instead of string-editing
  the INITIAL block.
- The `missing` vocabulary is classified once
  (`DELIVERED_REQUIREMENTS`, `VERIFIER_EVIDENCE_CODES`,
  `split_missing_requirements`, `verification_is_unavailable` in
  `core/header/contract.py`). A decision whose `missing` names only verifier
  evidence codes becomes `verification_unavailable` with an empty `missing`,
  which every host already routes to publish-unverified. Correlation
  failures keep their precise code, because the store answered.
- A rejection that does carry unmet requirements names them:
  `terminal_rejection_reason` appends "Unmet [AGENCY RESPONSE CONTRACT v1]
  lines: ..." in header order, on the claude/codex hook path and on the
  openclaw terminal path, including a replayed rejection (decoded from the
  stored row by `stored_missing_requirements`).
- The second measured shape -- no snapshot delivered at all -- now yields
  `header_snapshot_unavailable_context`, which tells the turn its values
  could not be read and not to reuse an earlier turn's header.
- Stale claim removed: the hermes turn-start instruction promised "seven
  lines" while the verifier had long checked five. The delivery rules that
  are genuinely host-specific stayed; the requirements moved to the contract.

## Acceptance

- [x] The finalization requirements for a turn are stated once,
      canonically, in-context; snapshots no longer carry divergent
      expectations. Evidence:
      `agency_runtime/core/header/response_contract.py`, the values-only
      instructions in `core/header/snapshot.py`, and
      `tests/test_response_contract.py::test_the_contract_is_delivered_once_beside_the_turns_first_values`
      (asserts exactly one contract marker per turn).
- [x] The 2026-09-01 withheld-response case is root-caused and covered
      by a regression test. Evidence: the root cause above and
      `tests/test_response_contract.py::test_unreadable_evidence_publishes_unverified_instead_of_naming_a_requirement`,
      with `test_a_turn_whose_snapshot_cannot_render_is_told_so` covering
      the second measured shape.
- [x] A rejection's `missing` list only names requirements that were
      delivered to the model in that turn. Evidence:
      `tests/test_response_contract.py::test_a_rejection_names_only_requirements_the_contract_stated`
      and `::test_missing_vocabulary_splits_delivered_requirements_from_agency_faults`.
