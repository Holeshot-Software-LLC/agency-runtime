---
title: "Supply rejected plans as untrusted repair data"
status: accepted
category: decisions
created: 2026-09-09
updated: 2026-09-09
tags: [workforce, inference, repair, privacy]
related:
  - docs/roadmap/issue-AR-425-preserve-planner-repair-context.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/worklog/2026-09-09-planner-repair-context.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0243
type: decision
deciders: [maintainers]
---

# ADR-0243: Supply rejected plans as untrusted repair data

## Context

A stateless provider cannot preserve valid parts of a prior answer it never
receives. The existing planner repair asks it to do so. The original native
Claude second rejection is unknown; the diagnostic reproduces only the first.

## Decision

The existing one-repair request includes the rejected planner object in a field
explicitly marked untrusted. It is bounded by the structured-response byte limit;
the normal complete prompt and request transport bounds also apply. It carries
no authority, worker selection or acceptance, and the replacement traverses every
existing validator. Other stages receive no new response-content field.
Known parser exceptions map by exact runtime-owned text to closed reason codes.
Terminal receipts retain codes only, never rejected plan contents or raw errors.
No additional calls, credentials, model changes or weakened assurance are allowed.

## Consequences

The planner can inspect the answer it must repair. Input tokens increase only on
repair, within existing bounds. This does not guarantee provider correctness or
prove the unknown original second rejection repaired. Native outcomes remain
separate evidence and failed receipts remain failed.

## Alternatives

Repeating the original request alone loses the previous answer. Deterministically
repairing unit topology would take planning authority away from inference.
Retaining raw answers in terminal receipts would violate content-free diagnostics.

Implementation03a82c3b is indexed in the worklog registry; artifact2b19cce6
retains exactly that production source.
