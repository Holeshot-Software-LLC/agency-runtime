---
title: "AR-413 installed HTTP status evidence"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, receipts, installed-evidence]
related:
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/worklog/2026-09-08-planner-reliability.md
supersedes: []
superseded_by: null
---

# AR-413 installed HTTP status evidence

## Source and focused checks

Implementation commit ed26177f281fba0e4aea807d2092574ea0e47e3d adds transport
status to workforce and hiring attempts and the bounded operator/terminal
projections. No provider selection, native policy, retry, prompt or budget changes.

The following command completed with 80 passed in 1.69 seconds:

```bash
python -m pytest tests/test_staffing_http_status.py \
  tests/test_staffing_failure_receipts.py tests/test_transport_failure_causes.py \
  tests/test_preflight_failure_diagnosis.py -q -W error
```

The HTTP-status tests exercise four failed workforce turns through the real
orchestrator and Store, all three projection fixed points, four hiring failures,
and 13 malformed/unknown values. Provider bodies, endpoints, headers and keys
are deliberately supplied to the projection and checked absent afterward.
Only exact integer statuses 100 through 599 survive; zero/absent stays absent.

## Installed failure demonstration

Canonical wheel and sdist built from exact source
d08c50084307a7da9e5e8c4285f20d97c42ea2ea in a clean local clone, after shared
Git configuration-name inspection exceeded the release helper's bounded output.
No release limits or shared Git configuration were changed. Strict Twine and
independent distribution verification against that exact commit passed.

Wheel: agency_runtime-0.1.0-py3-none-any.whl. SHA256:
fb385b5cbfa79301fb53b5c626815a7424dcbc50ab1e04552aa51bda922a819a.

An isolated no-dependency target install was imported first under Python -I.
A loopback HTTP server returned each status below through the installed
structured-provider transport. The installed workforce orchestrator executed
one failed turn per response, projected routing and wrote/read a real SQLite
Store using the repository's failure fixture. Four HTTP requests were observed.

| HTTP response | SQLite provider-attempt status | Turn accepted | Private body excluded |
|---|---|---|---|
| 401 | 401 | false | true |
| 408 | 408 | false | true |
| 429 | 429 | false | true |
| 502 | 502 | false | true |

This is an installed synthetic failure demonstration using real loopback HTTP,
not an external-provider success or a successful native Codex turn. It needs no
gateway log inference. Owner configuration, credentials and native policy were
not changed by the isolated test. The runtime installation on the owner host
was not replaced by this target installation.

## Broader verification

Named fast Python spine: 1151 passed, 3 skipped. Dashboard: 224 passed. Ruff
lint and deterministic routing gates passed. Decision-conformance passed with
source_unchanged true under umask 077; the initial ambient-umask run failed its
private-directory baseline and did not execute mutations. No exhaustive corpus,
compatibility matrix, coverage shards, Windows or CI dispatch was run.
