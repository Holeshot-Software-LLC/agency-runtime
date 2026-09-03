---
title: "AR-347 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-347
candidate_commit: 1bf7a2edaf6ff4af63526a753652456481ff7426
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/404
---

# AR-347 acceptance verification record

The parity backlog is reconciled and both strict gates now pass on main. The
matcher and allow-list work landed under AR-347 itself (`c7dee392`, then
`22a2dad9`); what remained on 2026-09-02 was two tracker labels and three
trackers left open for merged, verified work. With those applied,
`verify_tracker.py` passes with no allowance flag for the first time.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `ID_RE accepts the bracket, colon and hybrid tracker title styles, and rejects a bare AR-NNN with no separator` | 2026-09-02 | `scripts/verify_tracker.py:40-44` |
| 1 | command-output | `all three styles match and the bare form does not` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:18-22` |
| 2 | file | `the issue records the disposition applied to each mismatch class: labels, URLs, the #155 collision, PR-tracked items, six done-doc closes, the AR-237 completion and eight premature-close reopens` | 2026-09-02 | `docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:186-193` |
| 2 | file | `the reconciliation pass records the owner-authorized disposition applied to each mismatch` | 2026-09-02 | `docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:97-134` |
| 2 | file | `the nine-doc verification section records the per-doc verdicts behind the reopen and close decisions` | 2026-09-02 | `docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:135-181` |
| 2 | command-output | `every disposition is applied: the strict run reports 0 errors and 0 warnings over 372 items, so no state, label or URL mismatch remains` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-8` |
| 3 | file | `roadmap_history.py holds the shared allow-list semantics and bounds pre-tracker exemptions at AR-330, so a new item cannot smuggle itself onto the list` | 2026-09-02 | `scripts/roadmap_history.py:18-27` |
| 3 | file | `pre_tracker_entry_errors rejects any entry newer than that bound` | 2026-09-02 | `scripts/roadmap_history.py:60-80` |
| 3 | file | `validate_roadmap loads the allow-list and, under --require-tracker, reports only items that are missing a URL and not exempt` | 2026-09-02 | `scripts/verify_docs.py:1778-1791` |
| 3 | command-output | `the gate loads 132 exempt ids bounded at AR-330` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:24-27` |
| 3 | file | `the versioned pre-tracker allow-list itself` | 2026-09-02 | `docs/roadmap/pre-tracker-history.txt:1-136` |
| 4 | command-output | `verify_tracker.py exits 0 for 372 items with no allowance flag, 0 errors and 0 warnings` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-8` |
| 4 | command-output | `verify_docs.py --require-tracker reports zero tracker errors` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:10-16` |
| 4 | command-output | `each unindexed commit it names is a change under test on this branch, not a pre-existing failure` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:29-33` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-347.1-20260902-66f78235` | `aee765395b8e4572f920865102d4cc0d4b65e5fb3e5099d2ea9d123d1d1796c1` | 2026-09-02 | The cited ID_RE in scripts/verify_tracker.py accepts bracket, colon, and hybrid tracker titles, and the cited matcher output confirms all three styles match while the bare form does not. |
| 2 | satisfied | `AR-347.2-20260902-25bc3d76` | `aa9ea7dcdf0b05122865eb30a4bc658608ef58643500b6853a56e469334d9f16` | 2026-09-02 | The reconciliation and nine-doc audit excerpts record the owner-authorized label, URL, collision, PR-tracking, closure, completion, and reopen dispositions, and the cited strict verifier reports 372 items with zero errors and warnings. |
| 3 | satisfied | `AR-347.3-20260902-74fc42ac` | `f4eb6bc2a8495500e915a134b95faf812bf65d69cc6c29f917eab2720036a636` | 2026-09-02 | The versioned pre-tracker-history.txt allow-list is enforced by verify_docs.py, while roadmap_history.py rejects exemptions newer than AR-330, making --require-tracker applicable to new work. |
| 4 | satisfied | `AR-347.4-20260902-c0ead455` | `ee6ef1e9ea2e7239252d85b0f8c0a2eead7ad413dd0110c065814efdb1022744` | 2026-09-02 | The cited output shows verify_tracker exited 0 with 372 items and no errors or warnings, while verify_docs had zero tracker errors and failed only on two commits explicitly identified as changes under test on the branch. |
