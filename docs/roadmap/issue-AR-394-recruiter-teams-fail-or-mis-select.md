---
title: "AR-394: The recruiter stage ends most staffing turns, and the turns it does not end can staff an unrelated specialist"
status: open
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, recruiter, staffing, reliability, retrieval]
related:
  - docs/roadmap/issue-AR-391-recruiter-prompt-misstates-how-its-ranking-becomes-the-team.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-395-preflight-stage-vocabulary-is-incomplete.md
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/workforce/inference.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-394
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-394: The recruiter stage ends most staffing turns, and the turns it does not end can staff an unrelated specialist

## Problem

ADR-0207 closed AR-391 by telling the recruiter how its ranking becomes the
team and by handing a whole-team rejection back with a correction. The
measured install turns recovered. The recruiter stage is nonetheless still
where live staffing turns end, and the failure is not one shape.

Three distinct terminal shapes were observed in four consecutive live
reproductions of the real `UserPromptSubmit` hook:

1. **`selection_confidence_too_low` on one unit, then `staff_without_safe_team`
   on the repair.** A unit's confidence is the rank score of its lowest-ranked
   selected worker (`staffing_verifier.py:1107`, floor `min_confidence = 0.8`
   at `:57`). The repair then reported `required_count=1`,
   `ranked_executable_count=2`, `maximum_selected_per_unit=4` on the `domain`
   axis: of four ranked candidates only two were executable, and no safe team
   could be formed from them.
2. **`invalid_candidate`, then `staff_without_safe_team` on the repair.**
3. **`provider_call_timed_out`.** The recruiter profile carries
   `timeout_ms: 30000` while every deployment behind
   `task-agency-recruiter-v2` carries `timeout: 45.0`; the recruiter prompt
   measured 22,601 prompt tokens. This is the AR-392 ordering, live.

**The turn that did staff staffed the wrong specialist.** For the ask *"add
rate limiting to the public API gateway and write tests for it"* the accepted
proposal put `roblox-systems-scripter` and `threat-detection-engineer` on
`unit-implement-rate-limiting`, at confidence 0.9 against the 0.8 floor. The
verifier accepted it because nothing in the safety contract judges topical
fit; that is AR-370's question reaching the recruiter as a plausible-looking
team rather than as an empty retrieval.

The two halves are one problem. When retrieval hands the recruiter a
candidate set whose relevant members are not executable, the ranking is forced
deep, the lowest selected rank score falls under the floor, and the unit is
rejected; when it is not rejected, the same weak candidate set is what gets
staffed.

## Current state

**Measured 2026-09-04 on `main` at `8a4ea67d`.** The installed launcher
(`runtime-sha256-ce8a38b7…`) is byte-identical to the checkout for
`core/preflight_failure.py`, `core/structured_provider.py` and
`core/workforce/inference.py`, so the hook and the checkout run the same code
and the variation below is model nondeterminism, not a stale install.

Four live `UserPromptSubmit` hook runs against an isolated store copy
(`store.db_path` redirected to a scratchpad copy; the live store was read
only):

| session | outcome | terminal shape |
|---|---|---|
| `diag-ar394-0001` | failed | recruiter `selection_confidence_too_low` → repair `staff_without_safe_team` |
| `diag-ar394-01` | failed | recruiter `provider_call_timed_out` |
| `diag-ar394-02` | failed | recruiter `invalid_candidate` → repair `staff_without_safe_team` |
| `diag-ar394-03` | staffed | accepted (ask: *review this pull request for security issues*) |

A fifth run, the same hook entry point driven in process from the checkout
with the rate-limiting ask and the verifier instrumented, was **accepted**, and
its proposal is the second half of this issue: `unit-implement-rate-limiting`
selected `roblox-systems-scripter` and `threat-detection-engineer`, confidence
0.9, margin 0.9, delivery `load`, against floors `min_confidence = 0.8` and
`min_margin = 0.1`. Every other unit in that plan selected one plausible agent
at confidence 1.0.

Every one of the three failures also carried
`recall_reranker: provider_response_contract_invalid` from the local
`qwen3-14b-abliterated:latest` profile, so the reranker contributed nothing to
the candidate order on any failing turn.

On the live store, read only, across the last 400 preflight receipts, the
recruiter is the dominant failure: 408 recruiter attempts carry
`provider_response_contract_invalid`, against 107 that applied. The next
largest is `recall_embedding: dense_recall_projection_invalid` at 53.

## Why it matters

This is what an unavailable staffing header means today. The gateway is
healthy, the key reaches the hooks, the planner answers, and the turn is still
unstaffed because the recruiter stage cannot produce a team the verifier will
accept. Every downstream measurement that needs a staffed turn — AR-370
criterion 1, AR-393 criterion 5, the install battery — is gated behind it.

## Acceptance

- [ ] A recruiter rejection names which of the three shapes occurred and, for
      `staff_without_safe_team`, why the executable count fell short: whether
      the relevant candidates were absent from retrieval or present and
      ineligible.
- [ ] A unit whose ranked candidates cannot form a safe team is separated in
      the receipt from a unit whose recruiter reply was malformed.
- [ ] Topical fit of an accepted team is measurable: a recorded, reproducible
      check that would have rejected `roblox-systems-scripter` for a
      rate-limiting unit, or an explicit decision that fit is not the
      verifier's job and belongs to retrieval.
- [ ] The recruiter profile's `timeout_ms` and its deployments' `timeout` are
      ordered, with the runtime's deadline no lower than the gateway's.
- [ ] The reranker's `provider_response_contract_invalid` is either fixed or
      recorded as an accepted degradation with its effect on candidate order
      stated.

## Rejected alternatives

- **Lower `min_confidence`.** It would convert rejections into acceptances of
  exactly the teams the fourth run shows should not be accepted.
- **Treat this as AR-391 reopened.** ADR-0207's derivation account is present
  and correct in the failures observed; what is missing is upstream candidate
  quality and the account of why the executable set was short.
