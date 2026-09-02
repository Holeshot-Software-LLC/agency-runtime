---
title: "AR-377 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-377-hiring-payload-uncached-and-duplicated.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-377
candidate_commit: 65ec644de4c6f2c3fff4b78eaae1cf070e0a8064
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/551
---

# AR-377 acceptance verification record

Builder evidence for bounding the hiring critic's copy of the roster, cited
against the AR-377 implementation commit `65ec644d`; every verdict below comes
from one isolated single-check verifier run (`scripts/verify_acceptance.py`,
codex transport) that saw only that criterion and its own builder rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | command-output | `one hire's two roster-carrying calls: 231,682 then 88,210 then 49,408 prompt_tokens on 291 workers` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-377-evidence-20260902.txt:1-18` |
| 1 | file | `the before and after table recorded on the issue` | 2026-09-02 | `docs/roadmap/issue-AR-377-hiring-payload-uncached-and-duplicated.md#measured` |
| 2 | file | `_cited_workforce_agent_ids names every worker the candidate cites and every worker Agency's coverage rows name` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:972-1000` |
| 2 | file | `_cited_workforce projects the roster to those rows, with the redundancy it removes named` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1003-1026` |
| 2 | file | `_critic_prompt sends cited_workforce in place of complete_workforce` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1029-1052` |
| 2 | file | `_CRITIC_SYSTEM states what cited_workforce is and that the deterministic rejections already ran` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:117-128` |
| 2 | test | `test_critic_receives_only_the_rows_its_verdict_turns_on` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3047-3071` |
| 2 | test | `test_critic_sees_every_worker_agency_coverage_rows_name` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3074-3100` |
| 3 | test | `test_one_hire_makes_three_calls_and_carries_the_roster_once` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3103-3129` |
| 3 | test | `test_critic_receives_only_the_rows_its_verdict_turns_on` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3047-3071` |
| 3 | test | `test_critic_sees_every_worker_agency_coverage_rows_name` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3074-3100` |
| 3 | command-output | `the nine critic and call-count cases PASSED under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-377-evidence-20260902.txt:19-29` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-377.1-20260902-3c7b28eb` | `79ea5e4b8ef1716e228849a21a85cca2e5c1f2e0152a90b2c80bfd283aab1e96` | 2026-09-02 | The measured table and raw evidence report generator and critic prompt tokens for a complete hire before and after, with totals of 231,682 and 49,408 on the 291-worker roster. |
| 2 | satisfied | `AR-377.2-20260902-af092c6c` | `7c210e4b7bd9a2a11dd96840688ec1cfeca2e0f6d12af2623d01b746d1abe417` | 2026-09-02 | The excerpts show `_critic_prompt` supplies only `cited_workforce`, while `_CRITIC_SYSTEM` explicitly names prior rejection of role-identity duplicates, axis-subset duplicates, and unknown relationship targets. |
| 3 | satisfied | `AR-377.3-20260902-1e4565c9` | `c7796273b1e163907d8eb20e37d8910f81ea7ff5fcca8091512c244ba75a5570` | 2026-09-02 | The three cited tests directly assert exactly three calls, the full roster only in the generator prompt, exclusion of an uncited non-covering worker from critic input, and inclusion of all coverage-named workers; the cited run shows all three passed. |
