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
candidate_commit: ac1a5223548493f127922b0ae9b28b7f7cd91008
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
| 1 | command-output | `all three styles match and the bare form does not` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:12-16` |
| 2 | command-output | `no state, label or URL mismatch remains: the strict run reports zero errors and zero warnings over 372 items` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-7` |
| 3 | file | `roadmap_history.py holds the shared allow-list semantics and bounds pre-tracker exemptions at AR-330, so a new item cannot smuggle itself onto the list` | 2026-09-02 | `scripts/roadmap_history.py:18-27` |
| 3 | file | `pre_tracker_entry_errors rejects any entry newer than that bound` | 2026-09-02 | `scripts/roadmap_history.py:60-80` |
| 3 | file | `the versioned pre-tracker allow-list itself` | 2026-09-02 | `docs/roadmap/pre-tracker-history.txt:1-136` |
| 4 | command-output | `verify_tracker.py passes for 372 roadmap items with exit 0 and no allowance flag` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:5-7` |
| 4 | command-output | `verify_docs.py --require-tracker reports no tracker error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-347-evidence-20260902.txt:9-10` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
