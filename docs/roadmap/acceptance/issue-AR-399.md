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
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-399
candidate_commit: pending
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-399 acceptance verification record

Pending draft carried by the implementation branch. A planner reply that is
one complete object followed only by closing brackets or whitespace is now
parsed on the first ask and the attempt names the repair; every other
trailing text is still not JSON. The four replies that motivated the change
were captured live and replay through the parser (evidence section 2).

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the first complete object is decoded with raw_decode and kept only when the tail is closing brackets, fence ticks or whitespace; the object is re-read through the bounded loader and the repair is named` | 2026-09-05 | `agency_runtime/core/structured_provider.py:343-356` |
| 1 | file | `the existing whole-text and first-to-last-brace attempts run first, so a clean reply carries no repair` | 2026-09-05 | `agency_runtime/core/structured_provider.py:310-340` |
| 1 | file | `the applied attempt records the repair as a validation reason code` | 2026-09-05 | `agency_runtime/core/workforce/inference.py:1903-1914` |
| 1 | test | `test_one_stray_closing_brace_after_a_complete_object_is_trimmed_and_named covers five tails and asserts the object and the repair code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:31-38` |
| 1 | test | `test_a_repaired_reply_is_applied_on_the_first_ask_and_says_it_was_repaired drives _invoke_stage and asserts one applied attempt carrying the code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:122-132` |
| 2 | file | `any other trailing text leaves the tail check and returns not JSON; a text without an object returns None before any decode` | 2026-09-05 | `agency_runtime/core/structured_provider.py:310-356` |
| 2 | test | `test_trailing_prose_words_and_bare_prose_are_still_not_json and test_a_non_object_first_value_is_not_rescued` | 2026-09-05 | `tests/test_trailing_brace_reply.py:59-73` |
| 2 | command-output | `the shapes the parser still refuses, from the branch smoke` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-399-evidence-20260905.txt:25-30` |
| 3 | file | `the transport repair vocabulary is admitted for every stage beside the stage's own validation codes` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:29-31` |
| 3 | file | `the per-code gate accepts a repair code on any stage and still refuses anything else outside the stage vocabulary` | 2026-09-05 | `agency_runtime/core/preflight_failure.py:244-246` |
| 3 | test | `test_the_repair_code_survives_receipt_projection_for_every_stage covers six stages and an unknown code` | 2026-09-05 | `tests/test_trailing_brace_reply.py:141-147` |
| 3 | test | `test_a_clean_reply_carries_no_repair_code and test_a_clean_object_needs_no_repair` | 2026-09-05 | `tests/test_trailing_brace_reply.py:135-138` |
| 4 | command-output | `the four captured replies, each a complete object plus one stray brace, and each parsed with the repair named by the branch parser` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-399-evidence-20260905.txt:5-23` |
| 4 | test | `test_the_captured_reply_shapes_parse pins the two tails seen live` | 2026-09-05 | `tests/test_trailing_brace_reply.py:41-44` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

## Builder notes

New tests 10, all passing. The neighbourhood of 33 files gives 827 passed
with six failures that fail identically on `main`. No prompt changed; the
tolerance is parser-side and admits exactly one shape.
