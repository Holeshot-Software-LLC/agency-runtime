---
title: "AR-415 acceptance verification record"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, native, verification]
related:
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/roadmap/acceptance/evidence/AR-414-trusted-native-20260908.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-415
candidate_commit: 5b5a36c87e729b271353bd81986d6ea59983a34c
evidence_cutoff: 2026-09-08
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/778
---

# AR-415 acceptance verification record

## Builder evidence

This record cites bounded observations. Independent verification supplies verdicts.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | Nominal exclusions preserve read-only plan | 2026-09-08 | tests/test_workforce_intent.py:75-90 |
| 1 | command-output | Observed original failing regression and repaired result | 2026-09-08 | docs/worklog/2026-09-08-negated-request-scope.md#verification |
| 2 | test | Positive clauses retain implementation requirement | 2026-09-08 | tests/test_workforce_intent.py:93-99 |
| 2 | command-output | Installed exclusions and positive boundaries with unchanged gates | 2026-09-08 | docs/worklog/2026-09-08-negated-request-scope.md#installed-repair-checkpoint |
| 3 | command-output | Installed artifact and trusted native entry | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-414-trusted-native-20260908.md#installed-identity-and-trust |
| 3 | command-output | Native negative-clause read-only plan accepted | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-414-trusted-native-20260908.md#staffing-and-scope |
| 3 | command-output | Normal native Stop finalization | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-414-trusted-native-20260908.md#finalization |
| 3 | command-output | Explicit limitations and separate failed turn | 2026-09-08 | docs/roadmap/acceptance/evidence/AR-414-trusted-native-20260908.md#failure-boundaries-and-limitations |
| 3 | file | Canonical issue and tracker state | 2026-09-08 | docs/roadmap/issue-AR-415-respect-negated-change-requests.md#current-state |
| 3 | command-output | Worklog and verification | 2026-09-08 | docs/worklog/2026-09-08-trusted-native-acceptance.md#verification |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-415.1-20260908-f4edacdd` | `525401abf85da7e9deedfc2fa1a8b376c2008d28ae454eacc11971a04956d07d` | 2026-09-08 | tests/test_workforce_intent.py:76-90 asserts no violations for read-only plans with both cited negated phrasings, backed by _NEGATED_REQUEST_SCOPE in plan_policy.py:19-23 applied at line 586; the worklog lines 54-62 and 74-76 record the prior failure (mutation codes, 2 failed) before repair. |
| 2 | satisfied | `AR-415.2-20260908-2e332134` | `bf6cfdf9801b2bac70e863b2d495354af09e7dc304b7a1176cf6b8b3e32a8dfc` | 2026-09-08 | plan_policy.py:19-23,586 bounds the exclusion at punctuation and "but" and uses it in one place, so positive clauses still reach _code_mutation_violations (implementation, tests, review, evidence) and assurance reads the raw request; test_workforce_intent.py:93-99 asserts the violation. |
| 3 | satisfied | `AR-415.3-20260908-89659640` | `ebc1c230ce539f1f604f3af725256e85831a1dc070ac874a7f74aa9dbf76e89f` | 2026-09-08 | AR-414-trusted-native-turn.json shows the installed 8629e2ed wheel, negated prompt, one read_only advise unit, zero tool calls and accepted Stop hash; this agrees with the evidence doc limitations, the AR-415 issue state, both worklogs, and the repaired _NEGATED_REQUEST_SCOPE with its tests. |
