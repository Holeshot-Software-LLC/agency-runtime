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
candidate_commit: 9acf5f1e9b5afd914c5ce0d7f7777403258107a4
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
| 2 | file | `the matcher-fix section records the epic-label gap it surfaced and which trackers were corrected` | 2026-09-02 | `docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:84-95` |
| 2 | command-output | `every disposition is applied: the strict run reports 0 errors and 0 warnings over 372 items, so no state, label or URL mismatch remains` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-8` |
| 3 | file | `roadmap_history.py holds the shared allow-list semantics and bounds pre-tracker exemptions at AR-330, so a new item cannot smuggle itself onto the list` | 2026-09-02 | `scripts/roadmap_history.py:18-27` |
| 3 | file | `pre_tracker_entry_errors rejects any entry newer than that bound` | 2026-09-02 | `scripts/roadmap_history.py:60-80` |
| 3 | file | `validate_roadmap loads the allow-list and, under --require-tracker, reports only items that are missing a URL and not exempt` | 2026-09-02 | `scripts/verify_docs.py:1778-1791` |
| 3 | command-output | `the gate loads 132 exempt ids bounded at AR-330` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:24-27` |
| 3 | file | `the versioned pre-tracker allow-list itself` | 2026-09-02 | `docs/roadmap/pre-tracker-history.txt:1-136` |
| 4 | command-output | `verify_tracker.py exits 0 for 372 items with no allowance flag, 0 errors and 0 warnings` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-8` |
| 4 | command-output | `verify_docs.py --require-tracker reports zero tracker errors; its three remaining rows are worklog entries for this branch's own commits, which is the criterion's fail-only-on-changes-under-test case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:10-16` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
