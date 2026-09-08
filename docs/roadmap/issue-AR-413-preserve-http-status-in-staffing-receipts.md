---
title: "AR-413: Preserve HTTP status in durable staffing failure receipts"
status: open
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [observability, workforce, transport, receipts]
related:
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-codex-roundtrip-20260908.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-413
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/765
depends_on: []
blocks: []
---

# AR-413: Preserve HTTP status in durable staffing failure receipts

## Problem

Two fresh trusted Codex ordinary turns on September8 fail at the planner with
provider_http_status_error, but the durable receipt omits the HTTP status.
Diagnosing a timeout versus denied credentials or rate limiting still requires
separate gateway logs. This is not the previously fixed credential absence.

## Current state

Installed/main structured_provider.py preserves HTTPError.code in
StructuredProviderResult.http_status. WorkforceInferenceAttempt has no matching
field, and _attempt does not transfer it. Thus the loss occurs before the
durable preflight_failure_receipts projection. AR-392's result-level tests and
acceptance remain faithful historical evidence, not end-to-end status proof.

Exact live traces01a080ca-564e-7d41-81c9-b0e13b958a30 and
01a080ce-27ba-7871-96ec-0ac3eb662014 retain45774/45791ms durations and60000ms
deadlines but no status. Gateway logs at the first failure timestamp show
APITimeoutError and HTTP408; timestamp correlation is not a stored request-ID
join. The linked AR-404 receipt contains the bounded native evidence.

No implementation or acceptance pass is claimed. This is a focused follow-up
under existing ADR-0209, not permission to alter providers or retry budgets.

## Approach

Carry the actual transport status through staffing and applicable hiring attempt
types, routing and terminal-preflight projections to stored/operator evidence.
Use a bounded integer status with an explicit unknown legacy value; never infer
HTTP408 from elapsed time or the generic reason code. Preserve content-free
receipts: no response bodies, endpoints, headers, prompts or credential values.
Check every projection boundary, not only StructuredProviderResult.receipt().

## Dependencies

AR-392 supplies transport classification; AR-408 supplies terminal staffing
failure receipts. Neither requires reopening historical acceptance merely to
implement this newly demonstrated downstream gap.

## Acceptance

- [ ] Injected HTTP401/408/429/502 results retain their exact integer status
      through a complete failed workforce turn and SQLite readback.
- [ ] Routing/operator projections and relevant hiring evidence retain the same
      status; non-HTTP, unknown and legacy outcomes do not invent one.
- [ ] Malformed/unbounded status values fail the projection safely, and raw
      provider bodies, endpoints, headers and secrets remain excluded.
- [ ] One bounded installed failure demonstration records status without
      relying on gateway logs; native/provider policy remains unchanged.
