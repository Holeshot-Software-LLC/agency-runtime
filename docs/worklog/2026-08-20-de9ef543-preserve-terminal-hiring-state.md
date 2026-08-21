---
title: "Worklog detail: Preserve terminal hiring state in failure receipts"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [AR-119, AR-259, hiring, preflight, evidence]
related:
  - docs/worklog/README.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
supersedes: []
superseded_by: null
type: worklog
commit: de9ef543bcb8c11208f1f0ded3ebddf89157a438
short: de9ef543
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
---

# Worklog detail: Preserve terminal hiring state in failure receipts

## Purpose

The first exact-main Claude draw after the recruiter safe-team repair returned
valid planner and recruiter documents, then failed safely with a substantive
staffing gap. Its terminal receipt could not distinguish hiring that never ran
from a deferred terminal hiring event rolled back with failed atomic preflight.
Another provider draw would therefore have repeated an observability gap.

## Approach

The existing bounded `hiring_reason_codes` projection now includes an
allowlisted `hiring_status_<status>` code and
`hiring_inference_attempted` when `calls_used` is a positive integer. The
closed vocabulary covers the runtime's six terminal event statuses. The
receipt schema and Store migration remain unchanged, and old receipts continue
to decode as originally written.

## Challenges encountered

Successful deferred hiring events intentionally have an empty reason list, and
pending hiring state is intentionally discarded when preflight fails. Those
correct behaviors made the two source branches observationally identical after
the draw. The diagnostic report preserves that uncertainty instead of inferring
from elapsed time or absence of Store rows.

## Decisions and alternatives

The projection does not retain worker identities, notifications, prompts,
responses, pending contracts, or unrecognized status text. It does not change
provider routing, model budgets, selection, hiring eligibility, transaction
semantics, or retry policy. Expanding the receipt schema or persisting rolled-
back hiring rows was unnecessary and would have widened the privacy and
transaction boundaries.

## Verification

- Warning-strict preflight failure, Store-boundary, and dynamic-hiring tests:
  103 passed.
- Ruff check and format, documentation metadata, policy availability, and
  committed-whitespace checks passed before the ledger update.
- The proportional local harness reached the expected pre-ledger worklog gate;
  the complete fast result is recorded by the following checkpoint commit.
- No provider, host CLI, config mutation, installation, publication, hosted
  workflow, or live retry ran in this package.

## Follow-ups

- [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md): publish
  through a reviewed PR, reinstall exact main, and retain one decisive terminal
  receipt at the hiring boundary.
- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md): only after that
  diagnostic boundary is solid, continue the authorized three-harness staffing,
  hiring, dashboard-parity, and Linux-handoff sequence.
