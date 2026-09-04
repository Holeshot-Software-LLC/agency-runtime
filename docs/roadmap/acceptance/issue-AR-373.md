---
title: "AR-373 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/decisions/0202-read-the-recruiter-reply-where-no-safety-property-lives.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-373
candidate_commit: 4d0d7c1b66be8d2b847e6b4ce00534ea92a3040e
evidence_cutoff: 2026-09-03
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/537
---

# AR-373 acceptance verification record

Frozen at `4d0d7c1b`, the merge that brought the whole 2026-09-03 stack onto
`main`. The recruiter may cite the vocabulary Agency teaches it: the
nomination evidence charset admits the colon axis form
(`artifact:plan`, `domain:platform`) and, since ADR-0202, the underscore
ineligibility form (`agent_authority_mismatch`), while every bound that
carries a safety property and every typed identifier field are unchanged.
The live criterion is evidenced by the completed install turns of the two
eleven-wording runs on 2026-09-03 under strict mode.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_EVIDENCE_ARRAY is the nomination evidence schema whose item pattern admits the colon and underscore vocabulary Agency shows, with the count, uniqueness and length bounds of the identifier array` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:458-468` |
| 1 | file | `_valid_nomination_evidence accepts a bounded list of unique lowercase codes in the closed charset that admits : and _` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2455-2481` |
| 1 | test | `_CAPTURED_AXIS_ROW and _CAPTURED_FREEFORM_ROW are the rows captured verbatim from the recruiter on 2026-09-02, and test_the_axis_form_agency_teaches_is_accepted validates both through the validator and the candidate diagnostic` | 2026-09-03 | `tests/test_recruiter_evidence_vocabulary.py:30-65` |
| 1 | test | `test_the_ineligibility_vocabulary_agency_shows_is_accepted_as_evidence validates the captured forbidden row citing agent_domain_mismatch` | 2026-09-03 | `tests/test_recruiter_reply_residue.py:344-355` |
| 2 | file | `typed_staffing_requirements exposes _requirements, the builder of the axis tokens the recruiter is shown` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:475-484` |
| 2 | file | `typed_staffing_requirements is the public name the test derives its expectation from` | 2026-09-03 | `agency_runtime/core/workforce/staffing_verifier.py:600-603` |
| 2 | test | `test_the_vocabulary_agency_shows_is_the_vocabulary_it_accepts builds the tokens with the real builder over a typed plan and asserts every one validates` | 2026-09-03 | `tests/test_recruiter_evidence_vocabulary.py:68-114` |
| 3 | test | `test_every_safety_bound_survives asserts whitespace, uppercase, control characters, a leading colon, the length, uniqueness and count bounds, a non-list and non-strings are still refused` | 2026-09-03 | `tests/test_recruiter_evidence_vocabulary.py:117-130` |
| 3 | test | `test_typed_identifier_fields_are_not_widened pins the evidence pattern and the unchanged identifier pattern and shared bounds` | 2026-09-03 | `tests/test_recruiter_evidence_vocabulary.py:133-140` |
| 3 | file | `_IDENTIFIER_ARRAY keeps the hyphen-only pattern for the typed identifiers matched against contracts` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:470-480` |
| 3 | file | `_normalized_candidate_row keeps identity and score mandatory and refuses unknown fields; every validator bound then applies to the normalised evidence` | 2026-09-03 | `agency_runtime/core/workforce/inference.py:2490-2517` |
| 4 | command-output | `eleven install wordings under strict mode on the ADR-0201 runtime: turns 205, 206 and 305 completed with staffed teams and the critic's approval` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-384-option2-evidence-20260903.txt:47-76` |
| 4 | command-output | `the same eleven wordings on the ADR-0202 runtime: turns 204, 206, 207 and 209 completed with staffed teams and the critic's approval` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-373-AR-385-residue-evidence-20260903.txt:56-79` |
| 4 | test | `test_the_captured_deployment_shapes_are_staffed_first_time drives plan_and_staff_workforce through the four captured recruiter reply shapes and asserts each is staffed first time` | 2026-09-03 | `tests/test_recruiter_reply_residue.py:513-529` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-373.1-20260903-b2e14f0d` | `5074dafefa6f38f82f84f74733ffbdf88885cbaee4a9b1ded99ee1cadae8ad88` | 2026-09-03 | The excerpts show `_EVIDENCE_ARRAY` and `_valid_nomination_evidence` admit colon-delimited axis codes, while the captured-row test verifies both axis and freeform recruiter evidence pass validation and candidate diagnostics. |
| 2 | satisfied | `AR-373.2-20260903-b3faa490` | `07d2e582a8e81aff4c77198212f9e407793dddc4837de736a2bd63404c73681f` | 2026-09-03 | The cited test derives requirements from the real typed_staffing_requirements builder and passes those emitted tokens directly to _valid_nomination_evidence, asserting acceptance. |
| 3 | satisfied | `AR-373.3-20260903-fd37bf45` | `af00b3b70849b3339da654f1c63ea45130d8511675fa9b144d58de97738c2488` | 2026-09-03 | The cited tests explicitly pin all listed evidence bounds and the unchanged identifier regex, maxItems, uniqueItems, and maxLength, while inference.py shows the hyphen-only identifier pattern. |
| 4 | satisfied | `AR-373.4-20260903-d988bc79` | `fec07a2b4a04d2b527cdcf195532b5ed681ff3eea7b928b0121e69163b1d4896` | 2026-09-03 | AR-384 evidence lines 47-76 record turns 205, 206, and 305 as accepted with staffed teams under strict mode and critic approval, while the ADR-0202 residue table documents its runtime interpretation. |
