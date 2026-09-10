---
title: "AR-429 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, hermes, recruiter]
related:
  - docs/roadmap/issue-AR-429-ground-recruiter-specialties-in-unit-scope.md
  - docs/worklog/2026-09-09-hermes-nomination-relevance.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-429
candidate_commit: 0d89987db3135b72627daf9e9aed9e85eefef036
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/834
---

# AR-429 acceptance verification record

## Builder evidence

The builder supplies sources and does not judge. All three criteria satisfied on the first isolated pass.
Native staffing and finalization passed for one exact supplied-code case; no
all-host reliability, independent worker execution, or sole-cause claim is made.
The original failed receipts remain immutable. The actual native system prompt
contains the exact installed recruiter prefix plus the transport's JSON schema
suffix. Full recruiter/critic packets, API context and collected Store evidence
are in this snapshot beyond the excerpt limits. The two optional foundation
failures also occur on unchanged main and are deferred explicitly in AR-430.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact rejected request, mandatory nominations, critic veto and causal limit | 2026-09-09 | docs/roadmap/evidence/AR-429-original-request-and-veto-20260909.json:1-41 |
| 1 | file | Full relevant outcomes, activation qualifiers and exclusions from the selected contracts | 2026-09-09 | docs/roadmap/evidence/AR-429-original-selected-scopes-20260909.json:1-51 |
| 1 | file | Eligible correctness comparison card in each affected unit; full source packet retained | 2026-09-09 | docs/roadmap/evidence/AR-429-original-eligible-comparison-20260909.json:1-54 |
| 2 | file | Shared unit-scope rule with explicit positive specialized cases and preserved coverage/review | 2026-09-09 | agency_runtime/core/workforce/inference.py:371-399 |
| 2 | file | Unchanged inference-owned team classification and typed coverage rules | 2026-09-09 | agency_runtime/core/workforce/inference.py:444-486 |
| 2 | file | Bounded recruiter repair path includes shared rule and preserves valid-row boundaries | 2026-09-09 | agency_runtime/core/workforce/inference.py:487-533 |
| 2 | test | Actual initial/repair prompt delivery ends with enforced independent critic veto | 2026-09-09 | tests/test_workforce_inference.py:1560-1614 |
| 2 | file | Captured recipe21 prompt prefix and critic-approved selected units; full nominations remain in snapshot | 2026-09-09 | docs/roadmap/evidence/AR-429-native-nomination-summary-20260909.json:1-120 |
| 2 | file | Actual plan and binding graph retains independent static review after code/tests | 2026-09-09 | docs/roadmap/evidence/AR-429-native-plan-20260909.json:1-6 |
| 2 | test | Existing critic veto receipt regression unchanged and executed | 2026-09-09 | tests/test_strict_critic_doctrine.py:304-350 |
| 2 | file | Exact bounded/fast/artifact results and separately reproduced baseline failures | 2026-09-09 | docs/roadmap/evidence/AR-429-validation-20260909.json:1-53 |
| 3 | file | Exact invocation, completed Store run, authoritative final event, matching response hash and five headers | 2026-09-09 | docs/roadmap/evidence/AR-429-native-terminal-20260909.json:1-72 |
| 3 | file | All three inferred and retained cards match exact full native bytes | 2026-09-09 | docs/roadmap/evidence/AR-429-native-cards-20260909.json:1-67 |
| 3 | file | Exact native message IDs and content hashes bound to the same request and response | 2026-09-09 | docs/roadmap/evidence/AR-429-native-message-provenance-20260909.json:1-50 |
| 3 | file | Read-only native SQLite collection binds exact user and assistant final before card comparison | 2026-09-09 | docs/roadmap/evidence/AR-429-collect-20260909.py.txt:52-88 |
| 3 | file | Collector resolves immutable Store card bodies and compares complete inferred/retained sets | 2026-09-09 | docs/roadmap/evidence/AR-429-collect-20260909.py.txt:158-170 |
| 3 | file | Native API context raw bytes; complete 374-line file available in snapshot | 2026-09-09 | docs/roadmap/evidence/AR-429-native-api-content-20260909.txt:1-80 |
| 3 | file | Two packets captured, zero observer errors and owner config restored byte-for-byte | 2026-09-09 | docs/roadmap/evidence/AR-429-observer-restoration-20260909.json:1-7 |
| 3 | file | Exact finalized native response with three proposed tests and no execution claim | 2026-09-09 | docs/roadmap/evidence/AR-429-native-response-20260909.txt:1-40 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-429.1-20260909-091e5a21` | `636a2237267808827ccc2b626c05e47a5fc693022299a4ca98375435853be0d1` | 2026-09-09 | AR-429-original-request-and-veto json preserves the request, raw critic veto and explicit causal_limit, matching AR-428-observed-native-critic-packet lines 1735, 2195, 1034; selected-scopes json holds all three selected contracts, and eligible-comparison counts 246/83 match the retained packet. |
| 2 | satisfied | `AR-429.2-20260909-bcce1a9a` | `2a88370ff53f9d854c1c5dfa896b5a477f26eb032a1b561734cb52acd2bb35bc` | 2026-09-09 | inference.py:371-529 prefixes the shared unit-scope boundary (positive cases, inference authority, typed_recall, preserved independent review) to both recruiter and repair prompts; tests 1560-1614 and 304-350 enforce both prompts and the critic veto; validation JSON: focused 217 passed, 0 failed. |
| 3 | satisfied | `AR-429.3-20260909-bc0261d5` | `d2fb7b4f20ada3c7afac0b15267c13c6bf20f14232cbae997abc24555230bc22` | 2026-09-09 | native-terminal json shows exact-request run 20260909_213316_5f974b completed with authoritative accept, matching response hash and all_five_match headers; native-cards json and api-content file carry all three full card bodies; observer-restoration json: 2 packets, no errors, byte-exact restore. |
