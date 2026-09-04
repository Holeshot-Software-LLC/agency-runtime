---
title: "AR-395: Three real inference stages are not in the receipt's stage vocabulary, so their attempts are recorded as unknown"
status: done
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, receipts, observability, staffing]
related:
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
  - agency_runtime/core/preflight_failure.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/hiring.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-395
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-395: Three real inference stages are not in the receipt's stage vocabulary, so their attempts are recorded as unknown

## Problem

`project_preflight_provider_attempts` keeps only an allowlisted stage label
and rewrites everything else to `"unknown"`
(`preflight_failure.py:255-257`). The allowlist, `PREFLIGHT_PROVIDER_STAGES`
at `:116-128`, holds nine names:

    combined, planner, recruiter, recall_embedding, recall_reranker,
    hiring, critic, selector, unknown

The runtime labels its stages elsewhere, and three of the labels it actually
passes to `_invoke_stage` are missing from that set:

- **`subject`** — `inference.py:4373`, the ADR-0197/ADR-0208 gated subject
  derivation, which runs on the planner providers before the planner itself;
- **`security_review`** — `hiring.py`, route `workforce.hiring.security_review`;
- **`safety_repair`** — `hiring.py`, route `workforce.hiring.safety_repair`.

Every attempt those three stages record is written to the receipt as
`"unknown"`. Nothing else is lost — the reason code, the model identity and
the provider survive — but the receipt cannot say which stage spent the call,
and a reader must infer it from `model_group`.

The rewrite is not inert. `_project_validation_reason_codes`
(`preflight_failure.py:203-233`) dispatches on the stage name and returns `[]`
for anything it does not recognise, so a mislabelled stage also silently
drops any validation codes it might have carried.

## Current state

**Measured 2026-09-04 on the live store, read only, `~/.agency-runtime/agency.db`.**
Across the last 400 preflight receipts:

| stage on the attempt | attempts |
|---|---|
| `recruiter` | 549 |
| `planner` | 288 |
| `recall_embedding` | 221 |
| `recall_reranker` | 149 |
| `critic` | 77 |
| **`unknown`** | **64** |

62 of those 400 receipts carry at least one `unknown` attempt. Every one of
the 64 carries `model_group: task-agency-planner-v2` and
`provider_name: agency-planner` — the signature of the `subject` stage, which
borrows the planner's providers. Their reason codes are ordinary:
`structured_response_applied` 55 times, the rest rejections.

A live reproduction on 2026-09-04 shows the same thing inside one receipt: the
subject stage's two attempts read `unknown:provider_response_contract_invalid`
and `unknown:structured_response_applied`, and only the planner attempt after
them is named.

## Why it matters

AR-393 is an account of which stage spent what and why. A stage that cannot
name itself is a hole in exactly that account, and it is the newest stage —
the one ADR-0197 and ADR-0208 added — that falls into it. Any per-stage
measurement taken from receipts today undercounts the planner-provider calls
and attributes them to nothing.

## Acceptance

- [x] `PREFLIGHT_PROVIDER_STAGES` contains every label the runtime passes to
      `_invoke_stage`, in `inference.py` and `hiring.py` alike.
- [x] A test asserts that set equality directly against the labels found in
      the source, so a stage added later fails the suite rather than degrading
      into `unknown`.
- [x] A receipt written for a turn whose subject stage ran names `subject` on
      those attempts.
- [x] `unknown` remains reachable, and still means a stage the projection
      could not read.

## Rejected alternatives

- **Drop the allowlist and pass the stage through.** The allowlist is what
  keeps provider-authored text out of a durable receipt; the fix is to
  complete it, not remove it.
- **Infer the stage from `model_group`.** It is the ambiguity that caused
  this: the subject stage and the planner share `task-agency-planner-v2`.
