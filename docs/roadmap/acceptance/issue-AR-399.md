---
title: "AR-399 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-399-a-plan-object-followed-by-a-stray-brace-reads-as-prose.md
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/decisions/0215-accept-one-complete-object-with-a-trailing-bracket.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-399
candidate_commit: 894be044077685fcfcfc2942e17f02ab0f0c4f1c
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/671
---

# AR-399 acceptance verification record

Frozen at the review-fix commit of the implementation branch. A planner reply that is
one complete object followed only by closing brackets or whitespace is now
parsed on the first ask and the attempt names the repair; a stray bracket
followed by anything else, or no object, is still not JSON, while trailing
prose after a complete object stays accepted as the old span always did. The four replies that motivated the change
were captured live and replay through the parser (evidence section 2).

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the first complete object is decoded with raw_decode and kept only when the tail is closing brackets, fence ticks or whitespace; the object is re-read through the bounded loader and the repair is named` | 2026-09-05 | `agency_runtime/core/structured_provider.py:348-363` |
| 1 | file | `the existing whole-text and first-to-last-brace attempts run first, so a clean reply carries no repair` | 2026-09-05 | `agency_runtime/core/structured_provider.py:312-345` |
| 1 | file | `the applied attempt records the repair as a validation reason code` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:1903-1914` |
| 1 | test | `test_one_stray_closing_brace_after_a_complete_object_is_trimmed_and_named covers five tails and asserts the object and the repair code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:30-37` |
| 1 | test | `test_a_repaired_reply_is_applied_on_the_first_ask_and_says_it_was_repaired drives _invoke_stage and asserts one applied attempt carrying the code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:134-144` |
| 2 | file | `a stray bracket followed by anything else fails the tail check; a text without an object returns before any decode; raw_decode's ValueError and RecursionError both return not JSON` | 2026-09-05 | `agency_runtime/core/structured_provider.py:312-363` |
| 2 | test | `test_a_stray_bracket_followed_by_prose_and_bare_prose_are_still_not_json` | 2026-09-05 | `tests/test_trailing_brace_reply.py:59-66` |
| 2 | test | `test_a_text_without_an_object_is_refused_before_any_decode and test_a_reply_nested_past_the_recursion_limit_is_not_json_rather_than_an_error` | 2026-09-05 | `tests/test_trailing_brace_reply.py:76-85` |
| 2 | test | `test_trailing_prose_without_a_stray_bracket_is_accepted_as_before pins the pre-existing span behaviour the criterion leaves alone` | 2026-09-05 | `tests/test_trailing_brace_reply.py:69-73` |
| 2 | command-output | `the shapes the parser refuses and the ones the old span still accepts, from the branch smoke` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-399-evidence-20260905.txt:25-35` |
| 3 | file | `the transport repair vocabulary is admitted for every stage beside the stage's own validation codes` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:29-31` |
| 3 | file | `the per-code gate accepts a repair code on any stage and still refuses anything else outside the stage vocabulary` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:244-246` |
| 3 | test | `test_the_repair_code_survives_receipt_projection_for_every_stage covers six stages and an unknown code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:153-159` |
| 3 | test | `test_a_clean_reply_carries_no_repair_code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:147-150` |
| 3 | test | `test_a_clean_object_needs_no_repair` | 2026-09-05 | `tests/test_trailing_brace_reply.py:47-50` |
| 4 | command-output | `the four captured replies, each a complete object plus one stray brace, and each parsed with the repair named by the branch parser` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-399-evidence-20260905.txt:5-23` |
| 4 | test | `test_the_captured_reply_shapes_parse pins the two tails seen live` | 2026-09-05 | `tests/test_trailing_brace_reply.py:40-44` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-399.1-20260905-a18b4d84` | `8289d10e4a8427d57e6c7565193175e1aa82686d382f5e57fb8c4014240acbb2` | 2026-09-05 | structured_provider.py:312-363 keeps the first complete object when only brackets/whitespace follow and returns MODEL_TEXT_TRAILING_DATA_TRIMMED, wired via 846/879 onto the applied attempt at inference.py:1902-1914; tests/test_trailing_brace_reply.py:30-37,134-144 assert both. |
| 2 | satisfied | `AR-399.2-20260905-7bc0fc33` | `9e31c891b6edf97735b57ba23d832920282a72102f9df922828fe58e0f4f8035` | 2026-09-05 | structured_provider.py:312-363 returns (None,"") for a stray bracket with non-bracket tail, for text with no object (start<0, pre-decode), and on RecursionError from raw_decode; lines 849-854 map None to PROVIDER_MODEL_TEXT_NOT_JSON, and tests/test_trailing_brace_reply.py:59-82 pin all three. |
| 3 | satisfied | `AR-399.3-20260905-bd7b3d8b` | `5775324676d900154e380763ea7eb9ceca7781e3f8e0d44e9aac3caad41b7563` | 2026-09-05 | preflight_failure.py:31,245 admits the transport repair code alongside any stage vocabulary, and lines 271-288 route every stage (unknown included) through that gate; inference.py:1911-1913 with structured_provider.py:337 leaves a clean reply's codes empty, matching the cited tests. |
| 4 | satisfied | `AR-399.4-20260905-0f9c1a6b` | `f11311fb21e1e43915e7bb1d4c3cbf7016a71cee1f057a752e2ff1fb07ffc567` | 2026-09-05 | AR-399-evidence-20260905.txt:18-24 records all four captured replies replayed through _parse_model_text_with_repair, each parsed units=1 with the trailing-data repair plus "replies: 4"; structured_provider.py:312-363 and tests/test_trailing_brace_reply.py:40-44 confirm both recorded tails parse. |

## Builder notes

New tests 12, all passing. The neighbourhood of 33 files gives 827 passed
with six failures that fail identically on `main`. No prompt changed; the
tolerance is parser-side and admits exactly one shape. Only the HTTP transport
parses model text this way; the CLI transport is out of scope (ADR-0215).
