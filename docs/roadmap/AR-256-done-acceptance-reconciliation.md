---
title: "AR-256 done-acceptance reconciliation evidence"
status: active
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [documentation, governance, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: roadmap
evidence_cutoff: 2026-08-12
candidate_commit: b79a4138fd34e4f2e8abc01c5622d359e190e1dc
---

# AR-256 done-acceptance reconciliation evidence

This record explains every status or checklist correction made when AR-256
first enforced the rule that `done` means checked Acceptance. A checked box is
not new implementation evidence: it records an exact existing descendant
commit, test, live artifact, or merged pull request that already satisfied the
criterion. Unsupported labels were reopened. AR-161 is the one code-bound
historical exception because AR-197 removed its entire delivery surface before
the remaining gates could apply.

The candidate field identifies the clean ancestor against which existing
evidence and status were audited. This package changes governance and tests, not
runtime behavior; its clean checkpoint is recorded separately in the active
AR-119 capsule and worklog.

## Evidence-complete stale checklists

| Issues | Existing evidence used for reconciliation |
|---|---|
| AR-116, AR-118 | AR-204 exact installed Codex candidate and product run: `docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md`, product-proof sections; current child transport is historical and does not prove Rule 4. |
| AR-117 | Four-shard hosted passes recorded by AR-156 and the roadmap trace at `docs/roadmap/README.md`. |
| AR-121 through AR-124 | Criterion mapping in `docs/roadmap/AR-119-acceptance-evidence.md`; AR-123 also uses AR-236's 133 UI tests and browser QA. AR-124's planned-child transport is historical. |
| AR-128 | Its contemporaneous read-only control boundary is evidenced in the issue and trace commits; ADR-0117 later superseded the no-dashboard-bearer clause. |
| AR-133, AR-134, AR-136, AR-137 | Criterion-by-criterion implementation sections in each issue and trace commits `c741b24`, `0932410`, `b95d78a`, and `0b9849c`; AR-136 is historical transport, not current delivery authority. |
| AR-141, AR-142, AR-144, AR-146 | Each issue's implementation section and roadmap trace commits `a1efe31`, `0b9849c`, `567bd23`, and `c3ffe6a`. |
| AR-205 | Exact candidate `71faad8` and AR-204's installed product proof satisfy the zero-correction trial. |
| AR-212 | AR-204's later exact product run proves delivery/delegation/write; the stale box incorrectly named AR-214, so its wording is corrected. |
| AR-215, AR-217, AR-218 | Exact `71faad8` product artifact `docs/analysis/2026-08-03-ar-203-readme-story-evidence.html` and the AR-204 product-proof record. |
| AR-216 | Commit `a8913b50`, `tests/test_work_unit_integrity.py`, and the worklog row map all four required-file criteria. |
| AR-222 | Commit `9ff23e80` and `tests/test_work_unit_integrity.py` record the supported historical contract and all fourteen passing tests. |
| AR-224 | Commit `a498ceb1`, reduced-header fixtures, and AR-236's later fast/UI gates. |
| AR-227, AR-228 | Their issue verification sections and pull requests #236 and #237. |
| AR-238, AR-240 through AR-248 | Exact slice commits `b5bd549`, `0b6c059`, `e750593`, `f85074f`, `bdc24be`, `b4f7a2b`, and `da4d9e7f`, plus `docs/roadmap/handoffs/issue-AR-235.md`. AR-242 proves policy code only; AR-252 still owns live automatic promotion. |

## Reopened records

| Issue | Unmet evidence gate |
|---|---|
| AR-115 | No record proves its prompt-specific installed forbidden-specialist matrix in both configured-inference and no-inference modes. |
| AR-120 | Nightly ingestion remains unimplemented and has no successor. |
| AR-127 | Four criteria are evidenced, but no durable receipt proves the issue's exact historical full-suite command. |
| AR-235 | Its active capsule explicitly says the operator review plane remains incomplete. |
| AR-237 | The implementation exists, but its required pull-request gate has no PR evidence. |
| AR-250 | The plan/run upgrade flow was deferred without a successor issue. |
| AR-251 | Remaining roster, policy, and config card modes have neither implementation nor a successor. |

## Historical exception

AR-161 keeps its unchecked abandoned signing/licensing gates as faithful
history. AR-197 retired the Agency-owned Windows helper before public delivery.
`scripts/verify_docs.py` binds the exception to the exact Acceptance-section
digest, exact successor path, and provenance commit; any edit invalidates it.

## Limits

The verifier detects checklist/status drift and tampering with the one
historical exception. It cannot prove that a human truthfully checked a box;
this evidence record, Git review, and the cited artifacts remain the semantic
authority. Tracker status changes are separate outward-facing actions and are
not implied by these local corrections.
