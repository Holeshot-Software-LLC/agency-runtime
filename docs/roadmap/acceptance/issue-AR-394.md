---
title: "AR-394 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/selector/receipt_projection.py
  - tests/test_safe_team_shortfall.py
  - tests/test_retrieval_owns_topical_fit.py
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-394
candidate_commit: c2a923d4021f2b68a1d40696d07ac6d5f5f842b1
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/651
---

# AR-394 acceptance verification record

A `staff_without_safe_team` row now names *why* the team could not be formed,
from a closed eight-code vocabulary computed out of facts the repair contract
already established. The split criterion 1 asks for --- candidates absent from
retrieval against candidates present and refused --- is
`coverer_absent_from_retrieval` against `ranked_candidates_ineligible`, and the
two are decided by asking the same coverage question twice: once over the cards
the recruiter was shown, once over the whole roster.

The second half of the issue is answered by ADR-0213 rather than by code. The
verifier's 33 reason codes are all structural and none names topicality; the
roster held `api-platform-engineer` while retrieval offered
`roblox-systems-scripter`; so the accepted-but-inapt team is a supply failure,
and the fix belongs to AR-370. What the verifier owes instead is an account of
who failed to supply, which is exactly what the new vocabulary gives.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `SAFE_TEAM_SHORTFALL_CODES, eight closed causes, each commented with what it means` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:157-196` |
| 1 | file | `_safe_team_shortfall decides them in order: over-budget, starved complement, empty ranking, every ranked candidate refused, then the three coverage cases; eligible_coverers_by_requirement is scoped to the shown cards and the same question re-asked over the whole roster separates absent-from-retrieval from present-and-ineligible` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3222-3283` |
| 1 | file | `the classifier is called where staff_without_safe_team is raised, so every such failure carries one` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:3336-3343` |
| 1 | file | `the shortfall crosses the wire as a +segment and is projected into the receipt row as safe_team_shortfall` | 2026-09-04 | `agency_runtime/core/selector/receipt_projection.py:373-390` |
| 1 | test | `test_candidates_ranked_and_all_refused_is_an_eligibility_failure and test_a_coverer_the_roster_holds_but_never_showed_names_retrieval assert the two causes criterion 1 names, on the same shape of input` | 2026-09-04 | `tests/test_safe_team_shortfall.py:135-204` |
| 1 | test | `test_every_shortfall_reaches_the_receipt_on_its_own_failure is parametrised over the whole vocabulary and asserts each reaches project_nomination_failures beside the counts` | 2026-09-04 | `tests/test_safe_team_shortfall.py:239-264` |
| 1 | test | `test_the_classification_is_total_over_the_closed_vocabulary pins the set against the eight codes each asserted by a test above` | 2026-09-04 | `tests/test_safe_team_shortfall.py:219-236` |
| 1 | command-output | `317 of the 484 recruiter unit-failure rows in the last 400 live receipts are staff_without_safe_team, and 257 of those 317 carry no top_ranked_ineligibility, so the field a reader had to infer the cause from was absent four times in five` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-394-evidence-20260904.txt:3-15` |
| 2 | file | `the shortfall is refused on any code but staff_without_safe_team, at construction and again at projection` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:958-964` |
| 2 | test | `test_a_receipt_separates_a_short_team_from_a_malformed_reply builds one attempt holding both failures and asserts the short team carries the shortfall and the counts while the malformed row carries neither` | 2026-09-04 | `tests/test_safe_team_shortfall.py:281-316` |
| 2 | test | `test_a_shortfall_never_rides_on_a_malformed_reply and test_a_row_claiming_a_shortfall_for_another_code_is_refused_whole assert the separation cannot be crossed from either direction` | 2026-09-04 | `tests/test_safe_team_shortfall.py:266-332` |
| 2 | test | `test_a_detail_written_before_ar_394_still_projects asserts a pre-change detail parses unchanged and gains no shortfall` | 2026-09-04 | `tests/test_safe_team_shortfall.py:349-368` |
| 3 | file | `ADR-0213 records the decision: the verifier's contract is safety, and topical fit belongs to retrieval; it names why a fit floor is the same error as lowering min_confidence, and what the receipt owes instead` | 2026-09-04 | `docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md:56-91` |
| 3 | test | `test_the_verifier_names_no_topical_property_at_all asserts no code among the verifier's 33 contains a fit, topicality, relevance or subject term, and that selection_confidence_too_low is present -- the code that reads the recruiter's self-report and so clears a confident wrong answer` | 2026-09-04 | `tests/test_retrieval_owns_topical_fit.py:37-52` |
| 3 | test | `test_the_specialist_the_turn_should_have_found_is_in_the_roster reproduces the rate-limiting unit beside both contracts, so the fault is located at supply` | 2026-09-04 | `tests/test_retrieval_owns_topical_fit.py:118-131` |
| 4 | command-output | `every deployment behind task-agency-{planner,recruiter,critic,hiring-generator,hiring-critic,security-review}-v2 carries timeout 45.0, read live from GET /model/info across 133 deployments` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-394-evidence-20260904.txt:38-47` |
| 4 | command-output | `the six routed profiles that sat at timeout_ms 30000 are now 60000, and agency doctor reads every routed profile back at 60s or 120s -- no runtime deadline below the gateway's 45s` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-394-evidence-20260904.txt:49-52` |
| 5 | command-output | `recall_reranker applied 109 of 142 attempts, was provider_response_contract_invalid 29 times (20.4%) and returned no valid response 4 more, so it contributed nothing on 23.2% of the turns that ran it` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-394-evidence-20260904.txt:22-25` |
| 5 | file | `ADR-0213 records the degradation as accepted and states its effect: under dense_recall_mode additive the reranker never reorders, it can only add a card the typed baseline did not admit, so the cost is a smaller candidate set and not a worse order` | 2026-09-04 | `docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md:93-105` |
| 5 | file | `_apply_hybrid_recall returns the baseline typed recall and cards unchanged when reranked is empty` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2741-2742` |
| 5 | test | `test_a_failed_reranker_leaves_the_baseline_candidate_order_untouched drives _apply_hybrid_recall with an empty reranking and with an empty per-unit reranking and asserts the baseline order and cards are identical in both` | 2026-09-04 | `tests/test_retrieval_owns_topical_fit.py:64-115` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-394.1-20260904-5bee4fcc` | `7ac6d03102332cfe73b414ec5d7b3d388822227fc69f0cb8ac2b94c5f219bb85` | 2026-09-04 | Snapshot confirms _safe_team_shortfall (inference.py:3222-3280) separates coverer_absent_from_retrieval from the ineligibility causes, runs at the only staff_without_safe_team site (3336), projects beside reason_code (receipt_projection.py:373-390), tested in test_safe_team_shortfall.py:135-263. |
| 2 | satisfied | `AR-394.2-20260904-7e9590a9` | `985567edbf393bd820b138b8c264c0c175cbea069bcb119b3404e71511d77de6` | 2026-09-04 | Snapshot confirms inference.py:958-964 refuses a shortfall on any code but staff_without_safe_team and receipt_projection.py:370-377 refuses it again at projection; test_safe_team_shortfall.py:281-316 asserts the short-team row carries the shortfall and counts, the malformed row neither. |
| 3 | satisfied | `AR-394.3-20260904-38ecb645` | `37a5648fb6ab679d1293ffb6a8e33a3aea16f6ff649857ef5dc068730835b9e8` | 2026-09-04 | ADR-0213 (accepted) explicitly decides the verifier judges safety and retrieval judges fit, rejecting a fit floor; test_retrieval_owns_topical_fit.py:37-52 asserts no topical term among the codes, and staffing_verifier.py:132-168 confirms 33 structural codes including selection_confidence_too_low. |
| 4 | satisfied | `AR-394.4-20260904-a496a6bb` | `89a6b2e5a6caa0f498ea78a584badb25728a291b59d8a6996451125aedd522ed` | 2026-09-04 | AR-394-evidence-20260904.txt:38-47 shows task-agency-recruiter-v2 deployments at timeout 45.0 live; lines 49-52 show doctor workforce_profile_timeouts reporting agency-recruiter=60s after the raise from 30000ms. config_defaults.yaml:100,122 confirms the mapping, so 60s is not below 45s. |
| 5 | satisfied | `AR-394.5-20260904-cab13501` | `c5806c3c4190549380991418263356826857d739963b9377b6a6b39e938f7dcd` | 2026-09-04 | ADR-0213 (status accepted) lines 89-97 record the 29/142 contract-invalid rate as accepted and state its order effect: additive mode never reorders, so the cost is a smaller candidate set; inference.py:2742-2743 returns the baseline unchanged and the AR-394 c5 test asserts that. |

## Builder notes

**The issue named three failure shapes; the source had eight causes under one
of them.** Criterion 1 asked only for absent-from-retrieval against
present-and-ineligible. Writing the classifier as a total function over the
repair contract's facts produced six more, and two of them were already being
mis-told by the existing tests: `test_repair_exposes_required_budget_starvation_without_selecting_a_team`
staffs a unit whose four required agents exactly fill four slots, which is not
a coverage failure at all. `complement_slots_exhausted` is that case, and both
pre-existing wire-format assertions were updated to name what their fixtures
actually exercise.

**`no_eligible_coverer_in_roster` should be unreachable in production.**
ADR-0198 waives typed requirements no eligible contract serves, so a live row
carrying this code means the waiver did not fire. It is in the vocabulary
because the classifier is total, and it is worth watching for.

**The vocabulary is duplicated.** `receipt_projection` holds its own copy so a
receipt projection never imports the whole inference module;
`test_the_two_copies_of_the_vocabulary_agree` binds them, the same way the
recruiter validation vocabulary is already held together across
`preflight_failure.py` and `inference.py`.

**Criterion 4 was an operator change, made live.** `~/.agency-runtime/agency.yaml`
is not in this repository. The six routed profiles at `timeout_ms: 30000` were
raised to `60000`, above the gateway's 45s rather than equal to it, so the
gateway's own timeout fires with a real error body instead of the two deadlines
racing. The previous file is retained at
`agency.yaml.bak-ar394-20260904T192436Z`.

**The doctor's premise is now false for this gateway.** `_workforce_timeout_checks`
says the runtime "cannot read the deployment's" timeout. `GET /model/info`
returns `litellm_params.timeout` for all 133 deployments, so the check could
compare the two figures instead of printing one. That is a separate change and
is not made here.

**Parity, not zero.** The affected surface is 10 failed of 1663 selected on the
branch and the identical 10 on clean `main`; ruff reports the same 7 findings
and the same 11 files it would reformat in both trees. The
`decision-conformance` eval kills 182 of 182 mutations, including the one whose
`before` block had to be realigned to the new call site --- it must be run from
the conformance venv, since the baseline test run fails under the system
interpreter.
