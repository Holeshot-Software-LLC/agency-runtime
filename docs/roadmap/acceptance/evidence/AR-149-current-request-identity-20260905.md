---
title: "AR-149 current request-identity closure evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, dashboard, correlation, backlog]
related:
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
supersedes: []
superseded_by: null
---

# AR-149 current request-identity closure evidence

## Relevance and implementation

Unique per-request correlation remains relevant: a reused ID confuses the
operator's staffing, Store and failure evidence. The old defect report is not
current implementation state. Commit 6a3bdaa0 already repaired this boundary;
main e4255836 still clears cached request identity and previous headers before
each HTTP/1.1 dispatch. It preserves one identity inside RuntimeBoundary for
the request and its Store observations. No production change is needed.

## Current bounded demo and tests

Linux/Python 3.12, exact source e4255836:

```text
python -m pytest tests/test_dashboard.py \
  -k 'keep_alive or content_free_observations' -q -W error
4 passed, 157 deselected in 1.21s

python -m pytest tests/test_dashboard.py tests/test_dashboard_disconnects.py -q -W error
180 passed in 27.28s
```

The real loopback HTTPConnection test verifies that both requests use the same
socket, responses do not close it, the IDs differ, each matching dashboard
observation exists, and each ID reaches the Store boundary. Other real socket
tests prove a fresh ID for a protocol error and rejection of previous supplied
headers on malformed input, without echoing the private parser sentinel.
These tests run a disposable authenticated dashboard; no bearer is recorded.

The already-installed immutable runtime 5434836e and main e4255836 have
identical runtime/test/tool sources. The linked installed delivery retains its
1030-pass fast spine, 138 UI passes, 182 mutation kills and eight installed
smoke passes. No new native host or Windows result is inferred from that proof.

## Validation scope reconciliation

The original fourth criterion required the dashboard server and the entire
warning-strict corpus. ADR-0105 explicitly replaced that universal per-issue
completion prerequisite with focused checks and the named production spine;
the canonical issue preserves the original wording in a historical note.
This is not a claim that an exhaustive corpus ran, nor a change to a security
boundary, test threshold or product behavior.

A separate current UI coverage invocation passed all 138 cases but exited 1
at 91.12 percent functions versus the configured 93 percent floor. That finding
is AR-406. It is not evidence against per-request identity, and it is not
relabeled as a passing UI coverage gate. No exhaustive Python workflow ran.
