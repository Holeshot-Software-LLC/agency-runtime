---
title: "AR-404 oldest-first backlog reconciliation"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, evidence, supersession, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-404 oldest-first backlog reconciliation

## Owner-directed order

The owner requested: oldest first, one record at a time, PR, merge, then the
next; do not stop for routine approval. Windows work remains with the owner.
This replaces the earlier AR-349-first queue. Read-only investigation of the
current session's missing staffing credential/header evidence is set aside
until its relevant backlog package; no credential, trust or service change is
authorized merely by a record's age.

Order unfinished canonical records by original creation date, with stable AR
number breaking same-day ties. Each gets one explicit disposition: accepted
complete, superseded/irrelevant retirement, real bounded implementation, or
retained with its exact unresolved dependency/operator/platform evidence.
An umbrella whose children remain open cannot be completed just to move down
the list. Retain it and continue to the oldest actionable record. Do not
create 99 duplicate tracker issues or assume those records mean 99 defects.

At e5662d91 the queue is 141 unfinished records: 42 mapped plus 99 exempt
pre-tracker records. The legacy population was 104 before four verified
completions (AR-148/149/152/323) and one retirement (AR-139). Historical
snapshots remain intact; a retired mapped record changes the mapped count,
not the 99 legacy count.

## Sequential dispositions

| Order | Record | Disposition and evidence | Publication |
|---|---|---|---|
| 1 | AR-115 | Retire as superseded, not accepted. ADR-0222 replaces ADR-0078's heuristic staffing/six-field header with existing inference-only/canonical-five-field authorities. Original unchecked live gates retained; AR-119 explicitly absorbs the surviving outcome and AR-125 retains evaluation. Focused routing/header/credential/records: 183 passed (19.11s); fast spine: 1075 passed/three skips (68.74s). No runtime or live-state change in the retirement. | [PR #690](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/690) merged at d9ea419b; #127 closed NOT_PLANNED at 2026-09-05T23:47:12Z, read back. |
| 2 | AR-119 | Retain in_progress: relevant nine-rule/five-host umbrella with incomplete exact-candidate live evidence, AR-252 promotion, AR-253 dispatch/latency, AR-255/281 child proof, and AR-125 value/evaluation. Matrix still has three proven and 42 unproven cells at its August 18 candidate, not September certification. Reconcile stale current-state/capsule and R1 narrative; preserve all matrix rows, candidate, founding vision, criteria and failure history. | [PR #691](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/691) merged at 8b8b594e; [disposition comment](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132#issuecomment-5555649869); #132 intentionally remains open. |
| 3 | AR-120 | Retain open, partially implemented: normalized contracts, typed relationships, atomic snapshots and quarantine authority exist (219 focused tests pass, 15.34s). Independent enrichment-review evidence, owner-approved discoverability baseline, and proposed contract/confusion/evaluation refresh remain real gaps. Weekly cadence is intentional; do not restore nightly spending or automatic activation. Original acceptance unchanged; bounded remaining plan recorded. | Record-reconciliation PR pending; #133 intentionally remains open. |

After the merged AR-115 retirement, fresh enumeration confirms 41 open trackers
and 140 unfinished local records (41 mapped plus 99 legacy). Retaining AR-119
and AR-120 does not reduce either count. AR-125 is next after this disposition
merges. This is record reconciliation first, not a claim that retained
implementation work is complete.

Publication correction: GitHub interpreted the negated closing phrase in
PR #691's original body as a closure directive and closed #132 at 23:59:38Z.
Strict parity caught this during AR-120 review. The body was corrected, #132
reopened, and OPEN state plus the 41-issue count read back. It never represented
an acceptance verdict. Retained-item PRs use references without closing syntax.

The Codex-only hook refresh requested during AR-119 review returned exit 1
with activation required, unverified trust and a reported projection mismatch;
it did not supply live evidence or change any backlog disposition.
