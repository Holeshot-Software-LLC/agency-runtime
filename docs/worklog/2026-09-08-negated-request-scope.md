---
title: "Negated request scope and resumed native header evidence"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [planning, native, verification]
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/779
related:
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/decisions/0118-require-inference-owned-staffing.md
supersedes: []
superseded_by: null
related_issues:
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
---

# Negated request scope and resumed native header evidence

## Purpose

Resume AR-414 after native trust approval. Source baseline 9c277d0c;
installed baseline 6786aaa2. Inspect failures before changing prompts.

## Resumed observations

All eight native hooks are trusted, enabled and present exactly once. No trust
bypass, configuration override, provider change or credential replacement.
An observed installed arithmetic-mean staffing call accepted in 32.141 seconds:
subject2733ms, planner5123ms, embedding2804ms, reranker6928ms, recruiter9849ms,
critic4510ms. The observer prints response shapes only and returns results
unchanged; it is not an uninstrumented native run or an acceptance override.
A fresh median-review call failed at recruiter HTTP transport in 17.906seconds;
the first diagnostic omitted the numeric status, which cannot be reconstructed
from that output. One bounded retry accepted in18.118seconds, with subject21ms
and planner16ms warm-cache responses, recruiter2350ms and critic7021ms. These
samples do not prove general reliability; the earlier shape failure is not
reproduced and has not been declared fixed.

## Native diagnostic evidence

Normal installed Codex invocation, 2026-09-08T15:33:05Z through15:34:02Z,
57.119seconds, exit0, session01a081a6-c4bf-7ee3-916a-5dff92d0b43b,
trace01a081a6-c503-7150-9719-d1b6f3d7315d. Store has one failed run, one
preflight failure, no staffing receipt, no delegated specialist and no accepted
finalization. The response contains all five header fields, with loaded
agency-steward and Recruited via `failed; workforce_inference_failed;
planner:provider_response_contract_invalid; inference_invalid`. This is genuine
native diagnostic delivery, not successful staffing. Response SHA256
069fa373e1b592d3446ec145cfeb6ab48c679ed210ddf7973bf156bfcafefffd.

The first planner reply fails plan_missing_implementation,
plan_missing_test_implementation, plan_missing_independent_review,
plan_missing_test_evidence_review and plan_missing_release_verification;
the repair still fails the release requirement. Calls took5557ms and14172ms.
The supplied helper review said `not a request to change the repository or its
records`, but `_NEGATED_SCOPE` did not recognize this form. Token `change`
therefore triggered code-mutation requirements; `installed` triggered release
verification inside that mutation branch. This is deterministic, not evidence
that inference ignored a genuine implementation request.

## Approach and alternatives

Remove only explicitly excluded request clauses before the existing checks.
Bound nominal exclusions at punctuation/newlines and `but`, preserving positive
instructions. Do not exempt all read-only plans, disable completeness, add a
retry, pick a worker, or rewrite the native test to avoid the failing sentence.
The parser still has lexical limits outside these two explicit forms.

## Verification

Before repair, focused exclusion regressions:2failed,6passed. After the initial
repair, planner/inference/header suite184passed. An additional comma-boundary
case brings the final focused run to185passed. Native fixed-artifact
evidence follows after the source checkpoint and installation.

## Installed repair checkpoint

Implementation c1ef85662b01da7e8bbfa93917d6afdda1534aca, ledger6291746a,
merged PR779/d0bb4127 with merge ledgerbe65ddc8. Canonical clean-clone build,
strict Twine and independent distribution verification pass. Portable wheel
SHA25674988840e7f2e01aebd1db45ccef56372cfe07a1c87b7ce515b6df19577590bc.
All614installed package files match; installed `pip check` passes.
The isolated-import installed scope check returns zero violations for the
negative request and preserves implementation requirements across six positive
clause boundaries. This is deterministic installed evidence with zero provider
calls, not a native canary.

Named fast spine1151passed,3skipped in70.18seconds; focused185passed;
dashboard224passed; Ruff check and format778files; docs metadata1324files,
policy availability, worklog and release hygiene2499inputs pass. Routing eval
passes all thresholds. Bandit is unavailable in the verification environment;
no scan claim. No exhaustive corpus, cross-OS matrix, Windows test, hosted CI
dispatch or all-harness native claim.

The decision-conformance baseline and every curated mutation pass; overall
`passed:true` and `source_unchanged:true`. The baseline took102088ms. This was
the named bounded conformance gate, not the exhaustive corpus or CI dispatch.

Codex refresh completes at2026-09-08T15:42:44Z with dashboard opted out,
registered/enabled true, activation_complete false and restart_required true.
Plugin0.1.0+codex.07ad50ea4f52; bundle
7385d3a795c5bf7dcca4ced6c6e1ebf81f92159e27479a0c11e15b34b53531a2;
bindingd6a7490b19aeb99616f91c1f3d51d36dd038f789418792886fa4bba98d94ff4d.
Fresh native trust inspection reports8modified,0trusted. Unlike the prior
artifact's proven native diagnostic, this new artifact has no native run yet.
No bypass or further native retry follows that operator-owned gate.

## Follow-ups

AR-414 remains open for staffing reliability; do not substitute the successful
warm retry or diagnostic header for its unfinished gates. AR-415 owns the
confirmed nominal-exclusion bug and its installed verification.
