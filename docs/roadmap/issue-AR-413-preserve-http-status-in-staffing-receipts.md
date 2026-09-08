---
title: "AR-413: Preserve HTTP status in durable staffing failure receipts"
status: done
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
  - docs/worklog/2026-09-08-planner-reliability.md
  - docs/roadmap/acceptance/issue-AR-413.md
  - docs/roadmap/acceptance/evidence/AR-413-installed-http-status-20260908.md
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

Before this repair, installed/main structured_provider.py preserved HTTPError.code in
StructuredProviderResult.http_status. WorkforceInferenceAttempt has no matching
field, and _attempt did not transfer it. Thus the loss occurred before the
durable preflight_failure_receipts projection. AR-392's result-level tests and
acceptance remain faithful historical evidence, not end-to-end status proof.

Exact live traces01a080ca-564e-7d41-81c9-b0e13b958a30 and
01a080ce-27ba-7871-96ec-0ac3eb662014 retain45774/45791ms durations and60000ms
deadlines but no status. Gateway logs at the first failure timestamp show
APITimeoutError and HTTP408; timestamp correlation is not a stored request-ID
join. The linked AR-404 receipt contains the bounded native evidence.

The downstream fields are now implemented in workforce/hiring attempts and both
operator/routing and terminal-failure projections. Only exact integers100..599
are retained; absent/zero stays absent and malformed values are omitted. Legacy
receipt fixed points remain unchanged.83 focused tests pass, including actual
failed workforce turns through SQLite for401/408/429/502, hiring failures and
invalid/hostile metadata. A canonical independently verified wheel fromd08c5008
passes isolated-installed real loopback401/408/429/502 requests through workforce
and SQLite; every status is retained and response bodies excluded. This is a
synthetic failure fixture, not external-provider success. All four isolated
Codex acceptance verdicts are satisfied against65a387ed after explicit
non-HTTP/legacy tests were added. PR768 delivers this diagnostic correction;
owner runtime upgrade is separate from the isolated installed proof. The
ordinary native planner failure remains open under AR-404.

The owner separately authorized a bounded planner/gateway repair under AR-404.
Its live route experiment does not alter this code's staffing or retry policy.

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

- [x] Injected HTTP401/408/429/502 results retain their exact integer status
      through a complete failed workforce turn and SQLite readback.
- [x] Routing/operator projections and relevant hiring evidence retain the same
      status; non-HTTP, unknown and legacy outcomes do not invent one.
- [x] Malformed/unbounded status values fail the projection safely, and raw
      provider bodies, endpoints, headers and secrets remain excluded.
- [x] One bounded installed failure demonstration records status without
      relying on gateway logs; native/provider policy remains unchanged.
