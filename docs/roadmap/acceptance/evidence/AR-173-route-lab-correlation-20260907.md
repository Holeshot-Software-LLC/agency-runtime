---
title: "AR-173 current Route Lab correlation evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, diagnostics, correlation, backlog]
related:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/core/observability.py
  - agency_runtime/core/selector/explain.py
  - tests/test_dashboard.py
supersedes: []
superseded_by: null
---

# AR-173: Diagnostic Route Lab correlation

## Scope and first checkpoint

Linux / Python 3.12.3 / Node 22.23.2, September 7, 2026, after clean
6afcbcb523d55f4beb2339f2fa5b06c9ecae8a01 (PR #721 plus merge ledger).
No production change. New authenticated HTTP regression uses two actual social
explanations, with a guard that fails if inference is called. A wrapper observes
the real explain_route entry and then calls its unmodified implementation.

Every enabled request's trace is canonical UUIDv4 and already attached to the
active request observation before explanation. Responses preserve exactly
that trace. Each request has a separate client request UUID; its final dashboard
observation joins to the trace's domain-separated digest. The test restricts the
observation to allowed metadata, under 512 UTF-8 bytes, and rejects task, session,
bearer and prompt values. It verifies distinct traces, no run rows, no decision
IDs, zero routing-decision rows and no open session trace.

Additional guards reject trace allocation for invalid task input and master-
disabled requests. The existing bypass test still denies host/catalog access
and now also requires an empty routing trace. All profiles are temporary;
the owner's service, switch, roster and native hosts are untouched.

## Focused HTTP transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_dashboard.py -k 'route_lab_correlates_fresh or route_lab_master_disabled' -q -W error
```

Exact stdout, exit zero:

```text
..                                                                       [100%]
2 passed, 173 deselected in 2.33s
```

Ruff check passes and Ruff format reports the file unchanged after its initial
format. No failing product test was reproduced; the missing regression and
inaccurate record were the findings.

## Reconciliation

The existing explain_route docstring at lines 241–243 dates to e5f4a8c2
(July 18), before AR-173 (July 27). It explicitly retains diagnostic response
identity without durable turn evidence. The old issue narrative's persistence
claim was therefore not a missing implementation obligation.

ADR-0231 explicitly reconciles criteria 1/4/5 before review. Original wording is
preserved. Disabled/invalid calls do not fabricate traces; request observations
are emitted as log envelopes, not promised disk-retained or SQLite-persisted
turn records. The authenticated diagnostic response can include the task; the
content-free guarantee applies to correlation observations, not that response.

## Remaining verification

Full dashboard/explanation/observability checks, current UI floors, named spine
and record gates remain pending at this first clean checkpoint. No acceptance
verdict, production completion, native-host activation, Windows or release
claim is made from the focused test alone.

