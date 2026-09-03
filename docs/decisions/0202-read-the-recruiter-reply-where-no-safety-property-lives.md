---
title: "Read the recruiter's reply where no safety property lives, and never leave a rejected attempt blank"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recruiter, receipts, inference, staffing]
related:
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0202
type: decision
deciders: [owner]
---

# ADR-0202: Read the recruiter's reply where no safety property lives, and never leave a rejected attempt blank

## Status

**Accepted 2026-09-03.** Item 2 of the AR-383 capsule's next package: the
recruiter contract residue AR-373 owns, plus the two classes of rejected
attempt that reached the durable receipt blank and contradicted AR-385's
third criterion as worded.

## Context

The recruiter route on this installation is served first by a MiniMax
deployment that does not honour the JSON schema's `required` list or its
array types. After ADR-0201 the planner side of the install path was clean,
and four of the eleven measured turns still died at the recruiter on reply
shapes rather than on staffing judgment. Captured in process on 2026-09-03:

1. A forbidden candidate row arrived without its empty `positive_evidence`
   array (turn 202). The exact-key-set rule read it as
   `recruiter_candidate_row_shape_invalid` and the whole unit was repaired,
   although an absent array on a forbidden row carries no information the
   contract needs: evidence is validated and discarded, and the missing array
   is by construction empty. AR-373 had already recorded this shape.
2. The `units` array arrived wrapped one level too deep,
   `{"units": [{"units": [...]}]}` (turn 203). No row named a unit, so every
   unit surfaced as `missing_work_unit` with no diagnosis.
3. Evidence arrays arrived as objects whose keys were the codes (turn 203's
   repair), failing `recruiter_candidate_positive_evidence_invalid` although
   the keys were exactly the hyphenated codes the contract asks for.
4. The ineligibility vocabulary Agency itself shows in
   `typed_recall.candidates[].ineligibility_reasons`
   (`agent_domain_mismatch`) was cited back as negative evidence and refused
   for its underscore (turn 202's repair), the same defect AR-373 fixed for
   the colon form.
5. A repair reply was the empty object `{}` (turn 204). The accumulator
   raised a bare error, so the attempt reached both receipts as
   `provider_response_contract_invalid` with no validation record and no
   truncation record.
6. A reply the staffing verifier rejected (`selection_margin_too_low`, then
   `selection_confidence_too_low`, turn 207) reached the receipts the same
   way: the verifier's codes rode on the turn-level `staffing_reason_codes`
   but the attempt row itself was blank, because only nomination-contract
   failures were ever projected onto an attempt.

Classes 5 and 6 are what AR-385's third criterion forbids: a rejected
recruiter attempt with neither `validation_failures` nor a truncation record.
The AR-385 record could not honestly be frozen while they stood.

## Decision

1. **A candidate row is read as the deployment sends it where no safety
   property lives.** `_normalized_candidate_row` requires the identity fields
   (`agent_id`, `score`, `classification`), refuses any field outside the
   five the contract names, defaults a missing evidence array to empty, and
   reads a string-keyed object as its keys. Every bound the validator then
   enforces is unchanged: at most 16 unique codes of 1..128 characters in the
   closed charset, positive evidence on every required or acceptable row,
   negative evidence on every forbidden row, one classification per
   candidate, a known identity, a finite score in 0..1.
2. **The evidence charset admits `_`** beside `:` and `-`, because
   `agent_authority_mismatch` is vocabulary Agency shows the recruiter, exactly
   as `artifact:plan` was under AR-373. The typed identifier charset that is
   matched against contracts is not widened.
3. **One wrapper is unwrapped and no further.** `_nomination_rows` accepts
   `{"units": [{"units": [...]}]}` as the inner array; two levels, an empty
   object, a bare list or a string read as no rows at all.
4. **A reply that is not a units object is recorded, not thrown.** The
   accumulator raises a nomination failure of `missing_work_unit` for every
   planned unit (or every unit of the repair) with the new closed diagnosis
   `recruiter_response_shape_invalid`, so both receipts carry the units and
   the diagnosis, and the repair prompt asks for the whole object again. The
   reply bound moves from the unit count to four times it, because rows for
   unknown units were already dropped by identity.
5. **A verifier rejection projects onto the attempt row.**
   `project_nomination_failures` accepts the verifier's detail prefix and its
   `unit=code` rows, with `global` for a finding that names no unit, bounded
   to the receipt's sixteen rows and to the code charset the preflight receipt
   already admits for `staffing_reason_codes`. Both receipts read the same
   function, so they agree.

Not done, by design: accepting prose evidence, unknown fields, a missing
identity or score, a reply with no readable rows as anything but a failure,
or verifier codes outside the closed charset. The deployment's structurally
malformed 941-token reply (turn 304) is refused by the transport before the
parser sees it and stays a `failed` attempt with `provider_no_valid_response`.

## Consequences

- The four captured shapes are staffed first time; the empty-object reply is
  recorded per unit and repaired; a verifier rejection is readable on the
  attempt row without the capture harness. Pinned in
  `tests/test_recruiter_reply_residue.py` from the captured rows, with one
  curated conformance mutation on the projection.
- AR-385's third criterion is true again by the letter: every rejected
  recruiter attempt carries `validation_failures` or a truncation record.
  A `failed` attempt (no valid response) is not a rejected one.
- The receipt vocabulary grows by one recruiter validation code and by the
  verifier's own codes on attempt rows; no receipt schema or store migration
  is needed because both ride in existing fields.
- A row that omits its evidence array is now silently completed, so the
  receipts no longer show that the deployment omitted it. The diagnosis
  codes that remain (`recruiter_candidate_row_shape_invalid` for unknown or
  missing identity fields, the evidence codes for prose) still name the
  deployment's real deviations.
- Live re-measurement on the same eleven wordings is recorded in the AR-373
  and AR-385 issues.

## Alternatives

- **Keep the exact-key-set rule and let the repair loop pay.** Rejected: the
  repair spends the strict budget's one recruiter repair on a row whose
  missing field carried no information, and the repair reply from the same
  deployment often carries the next shape defect.
- **Widen the evidence field to free text.** Rejected: prose is the one
  thing the charset exists to keep off the wire; the underscore is a closed
  vocabulary Agency emits.
- **Carry verifier codes as `validation_reason_codes`.** Rejected: the
  preflight receipt's recruiter allowlist is closed to the recruiter's own
  diagnosis codes and refuses the whole list on one stranger, and the rows
  form already carries the unit the code names.
- **Fix the deployment's schema handling at the gateway.** Operator
  territory (the LiteLLM alias's `json_schema` strictness); this record
  makes the runtime honest about the replies it does receive.
