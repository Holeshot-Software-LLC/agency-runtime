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
candidate_commit: pending
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/551
---

# AR-377 acceptance verification record

Pending draft. Builder evidence for bounding the hiring critic's copy of the
roster, cited against the working tree; the record freezes to the
implementation commit once that commit is an ancestor of `HEAD`, and
verification rows are written only then.

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
