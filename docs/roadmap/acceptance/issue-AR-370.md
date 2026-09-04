---
title: "AR-370 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0211-give-retrieval-a-subject-and-name-the-empty-turn.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-370
candidate_commit: 0e5a96f3f2cd08074159c6b80d67eb1c3fd4598b
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/518
---

# AR-370 acceptance verification record

Builder evidence at `0e5a96f3` for criteria 3 to 6. Criterion 2 was closed by
ADR-0208 and is evidenced in the AR-383 record. **Criterion 1 is not met**: its
mechanism is in place and the deterministic half is measured here, but the
end-to-end claim needs a staffed turn against the live roster. See "Not
established here".

Everything below is deterministic: no provider call is made and no credential
is required.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 3 | file | `domain_expansion.py is deleted; the routing query is the affirmative intent of the refined message, with the reason stated where the call was` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:487-495` |
| 3 | file | `the explain payload keeps its domain_expansion block, reporting applied false and retired true, rather than the field vanishing under readers` | 2026-09-04 | `agency_runtime/core/selector/explain.py:189-199` |
| 3 | test | `test_the_domain_expansion_table_is_gone asserts the module no longer imports and the symbol is off the package` | 2026-09-04 | `tests/test_selector.py:128-148` |
| 3 | test | `test_no_query_is_expanded_with_curated_discipline_vocabulary asserts on the query the pipeline builds, because litellm legitimately survives as a provider adapter name and a grep would report a false positive` | 2026-09-04 | `tests/test_selector.py:151-181` |
| 3 | command-output | `the module is removed, zero expand_query references remain in agency_runtime, and no stack noun survives in the selector package` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-370-evidence-20260904.txt:6-10` |
| 4 | file | `resolve_bare_reference resolves a URL to its own distinctive labels and a deictic to the turn's typed subject hints, bounded to eight tokens and 120 characters, inventing nothing` | 2026-09-04 | `agency_runtime/core/selector/reference_resolution.py:130-176` |
| 4 | file | `whether the request still names a subject is asked with retrieval_has_signal, the zero-signal trigger's own predicate, rather than a local list of words that do not count` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:475-486` |
| 4 | file | `mentions_bare_reference gates the catalog pass to turns that contain a URL or deictic at all` | 2026-09-04 | `agency_runtime/core/selector/reference_resolution.py:96-107` |
| 4 | file | `the resolution reaches the routing receipt as reference_resolution, bounded and content-free` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:915-920` |
| 4 | test | `eight tests pin URL resolution, deictic resolution from context, an honest unresolved deictic, a request that names its own subject being left alone, the bound, the precheck, and the receipt` | 2026-09-04 | `tests/test_retrieval_subject_resolution.py:52-140` |
| 4 | command-output | `install this: <url> resolves to zcode and steers the query; a request naming its own subject is untouched; a deictic with no context is detected and honestly unresolved` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-370-evidence-20260904.txt:63-74` |
| 5 | file | `request_underspecified and no_relevant_candidate, with the rule that a turn whose inference never answered and a turn the recruiter judged both keep their own code` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1441-1520` |
| 5 | file | `the codes ride on the staffing decision's abstention reasons, the route workforce_credential_env_unset takes to the receipt and the disclosure` | 2026-09-04 | `agency_runtime/core/selector/pipeline.py:1523-1548` |
| 5 | test | `seven tests pin the three cases apart, plus a staffed turn and an inference failure carrying no retrieval code, and the code reaching the decision the receipt reads` | 2026-09-04 | `tests/test_retrieval_subject_resolution.py:146-262` |
| 5 | command-output | `the four shapes: underspecified, empty roster, recruiter verdict, inference never answered` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-370-evidence-20260904.txt:76-80` |
| 6 | file | `the corpus gains service-operations-engineer and monitoring-engineer, whose nouns are host-side verbs rather than "installation"` | 2026-09-04 | `agency_runtime/core/evals/data/routing_v1.py:188-232` |
| 6 | file | `one case per operational verb, phrased as a work statement, with the reason that a deterministic recall eval cannot make an inference call` | 2026-09-04 | `agency_runtime/core/evals/data/routing_v1.py:234-302` |
| 6 | test | `test_the_corpus_carries_a_case_for_every_operational_verb and test_every_operational_verb_retrieves_its_specialist` | 2026-09-04 | `tests/test_retrieval_subject_resolution.py:263-310` |
| 6 | command-output | `before: seven of eight retrieved nothing. after: all eight retrieve their required specialist, seven at rank one` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-370-evidence-20260904.txt:12-48` |
| 6 | command-output | `every published threshold still passes; precision@3 rose from 0.6071 to 0.6364 and top-1 relevance stays 1.0` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-370-evidence-20260904.txt:50-61` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 3 | satisfied | `AR-370.3-20260904-51924b72` | `6bdef52ade61a1a333bf19439446d10411ca13cde04141c814d79f6b78187d03` | 2026-09-04 | Snapshot shows selector/domain_expansion.py absent, no _DOMAIN_EXPANSIONS or expand_query anywhere in agency_runtime source, pipeline.py:523 sets routing_query = affirmative_intent(refined) with no expansion, explain.py:194-199 reports retired true, and tests/test_selector.py:129-180 assert both. |
| 4 | satisfied | `AR-370.4-20260904-2c5f8878` | `c888614ca02a71e5cb622f6d13676832d2f93ce8baed2fbd5f9e73d758d19962` | 2026-09-04 | Snapshot pipeline.py:512-523 resolves a bare URL or deictic and appends the subject to refined before routing_query is built for retrieval, and pipeline.py:534 plus 927 carry reference.receipt() into the routing receipt; test_retrieval_subject_resolution.py:121-137 pins this end to end. |
| 5 | satisfied | `AR-370.5-20260904-8c35e650` | `ae475fc0f647960b0f695dd0db89224d2dfe225347d8a0e4412c05e4dfa6c3b6` | 2026-09-04 | Snapshot pipeline.py:1598-1676 defines request_underspecified distinctly from no_relevant_candidate and returns no code when the recruiter judged a real candidate set; wired in at :2137, with tests/test_retrieval_subject_resolution.py:167-262 and evidence file lines 76-80 pinning the cases apart. |
| 6 | satisfied | `AR-370.6-20260904-c7bce342` | `b3aaf1443f5651729866aadddb0de6c6bb857ad635b47d5291558b0002ff3a56` | 2026-09-04 | routing_v1.py:244-301 defines eight verb-* cases and line 568 splices them into ROUTING_CASES (metrics show 45 vs main's 37); tests at test_retrieval_subject_resolution.py:263-310 pin the exact verb-id set and assert each retrieves its required specialist, so the table cannot silently regress. |

## Builder notes

New tests 19 (17 in the new file, 2 replacing the retired expansion tests). The
affected selection is 2246 passed, 18 failed; all 18 fail identically on `main`
at `82a85f48` and none is touched by this change. `main` passes 2207 on the
same selection.

Three regressions were caught and fixed rather than accepted:

The new `service-operations-engineer` card displaced `technical-writer` as
top-1 on the existing `route-readme` case, because a bare "installation" also
matches "rewrite the README installation guide". The card's nouns were changed
to host-side verbs, which restored it; top-1 relevance is 1.0, not the 0.975 it
briefly measured.

The reference resolution first ran `retrieval_has_signal` on every request. That
is a full pass over the eligible catalog, and it took the routing eval's
cache-hit p95 from 0.19 ms to about 70 ms. It is now gated behind a cheap
URL-or-deictic precheck.

The unstaffed classification first fired on turns where inference never
answered, which broke all three chaos staffing shapes: a provider timeout is
not the request's fault nor the roster's. It now returns nothing when the
inference mode is unavailable or invalid, and nothing when the decision already
carries `no_safe_sufficient_team`.

## Not established here

**Criterion 1 is not met.** "Retrieval runs on an inference-derived work
statement" has its mechanism in place -- ADR-0197's zero-signal trigger buys the
typed classification call, and ADR-0208 carries the inferred subject into the
recall query -- and the deterministic half is measured above: retrieval answers
correctly once the query states the work, for all eight verbs. What is not shown
is the end-to-end claim, that `configure the gateway` and `install this: <url>`
retrieve a relevant specialist from the live 291-contract roster without the
user supplying vocabulary. That needs a staffed turn, and staffing was
unavailable throughout this session.

The eight verb cases are measured against the 18-card corpus catalog, not the
live roster. They guard the property the fix depends on; they are not a
substitute for the live measurement.
