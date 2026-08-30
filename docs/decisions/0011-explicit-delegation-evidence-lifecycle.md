---
title: Model delegation as an explicit evidence lifecycle
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [delegation, evidence, state-machine]
related:
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-59-event-driven-delegation-scheduler.md
  - docs/roadmap/issue-AR-69-require-correlation-complete-cli-delegation-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0011
type: decision
deciders: []
---

# ADR-0011: Model delegation as an explicit evidence lifecycle

## Context

Detecting multiple independent work units does not prove that another specialist or worker was invoked. Earlier output could imply delegation merely because routing suggested it.

## Decision

Persist delegation as a stateful evidence lifecycle. Work-unit detection records suggested events. A supported delegation tool call promotes the matching event to delegated or completed. A backend failure or timeout records skipped or failed with a concrete reason. With no tool call, the event remains suggested.

Finalization and pre-verification compare the visible delegated line with stored events. They must not turn a suggestion into an execution claim.

## Consequences

- The system distinguishes opportunity, attempt, execution, completion, and failure.
- Header claims can be audited against tool events.
- Backends must report enough identity to match a call to the correct session and recommendation.
- Operators see explicit blockers instead of a misleading bare none.

## Alternatives

- Treat work-unit detection as delegation. Rejected because planning is not execution.
- Infer delegation from final prose. Rejected because prose has no trustworthy lifecycle identity.
- Record only successful calls. Rejected because skipped and failed attempts are essential operational evidence.

## Provenance

Commit 886d6cf began capturing specialist and delegate tool events. Commit 8b377b1 established the durable delegation event lifecycle, cross-host enforcement, evaluation, and smoke coverage. Commits 3954d35 and d9379f3 extended that lifecycle to bounded CLI backends.
