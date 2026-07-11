---
title: Worklog
status: active
category: worklog
created: 2026-07-10
updated: 2026-07-11
tags: []
related: []
supersedes: []
superseded_by: null
---

# Worklog

This registry connects repository history to the roadmap and to optional detail records that preserve reasoning too large for a commit subject. Rows are chronological, and commit subjects are copied verbatim from Git.

## Ongoing policy

- Add every substantive commit to this registry with its short SHA, commit date, exact subject, related roadmap issue when known, and detail-file link when one exists.
- Add a detail file from [TEMPLATE.md](TEMPLATE.md) when a commit carries durable reasoning: approach, notable challenges, decisions or rejected alternatives, or follow-up work. Historical detail files are not backfilled; they begin going forward.
- A substantive commit must be indexed by an immediately following ledger update. A commit that changes only `docs/worklog/**` and the reciprocal commit cell in `docs/roadmap/README.md` must use the exact subject prefix `docs(worklog):` and is exempt from requiring its own row or detail file. No other paths are allowed. The updater and verifier recognize only this narrow exception, which allows the repository to return to a clean state without an infinite chain of ledger commits.
- Never rewrite a historical subject to remove a name or change its wording. Flag provenance-sensitive terms in the notes instead.
- Link only to records and tracker items for this repository. Do not add sibling-repository paths or dependencies.

## Commit index

<!-- worklog:start -->
| Short SHA | Date | Subject | Related issue | Detail |
|---|---|---|---|---|
| `5eb4de1` | 2026-07-08 | Add complexity tier to model header + fix post_api_request race condition | null | null |
| `cfc7d38` | 2026-07-08 | Fix dynamic model resolution: capture actual model from response, not SpendLogs | null | null |
| `886d6cf` | 2026-07-08 | Fix: post_tool_call hook captures specialist loads, not just skills | null | null |
| `2434f30` | 2026-07-08 | Wire portable agency_runtime into live Hermes plugin (Step 2-3 cutover) | null | null |
| `3b39f58` | 2026-07-09 | config-first secrets, doctor auth, packaging hardening, portability fixes | null | null |
| `c2d1274` | 2026-07-09 | fix: pre_llm_call always injects routing, pre_verify enforces specialist loading | null | null |
| `dc0be8d` | 2026-07-09 | feat: multi-provider fallback chain with config-first auth | null | null |
| `a7bba3a` | 2026-07-09 | feat: one-command install, on/off toggle, comprehensive README | null | null |
| `8f6d320` | 2026-07-09 | docs: add agency-runtime session handoff | null | null |
| `8b377b1` | 2026-07-09 | feat: harden agency runtime delegation evidence | null | null |
| `442b91a` | 2026-07-09 | chore: untrack generated code indexes | null | null |
| `3b24614` | 2026-07-09 | feat: harden yolo roster sync and specialist preflight | null | null |
| `42f6580` | 2026-07-10 | feat: add routing explain receipts | [AR-01](../roadmap/issue-AR-01-selection-explain-receipts.md) | null |
| `6dc35cd` | 2026-07-10 | fix: repair mcp finalization tool | null | null |
| `bb0c12d` | 2026-07-10 | fix: keep http finalize evidence on session id | null | null |
| `9e57cf1` | 2026-07-10 | fix: sanitize http server error responses | null | null |
| `4f477f6` | 2026-07-10 | fix: preserve delegate type errors | null | null |
| `3954d35` | 2026-07-10 | fix: bound cli delegation waits | null | null |
| `d9379f3` | 2026-07-10 | feat: add json delegate results | null | null |
| `2235d7e` | 2026-07-10 | fix: avoid shelling out for adapter availability | null | null |
| `901a880` | 2026-07-10 | fix: lower trivial_msg_threshold to 8 + persist nontrivial via store | null | null |
| `be4f52f` | 2026-07-10 | fix: trivial threshold, removed 'next'/'status' from trivial patterns, added DEFAULT orchestrators | null | null |
| `31443bc` | 2026-07-10 | feat: bundle full 16-action companion policy, add agency policy CLI, surface companions in route | null | null |
| `badb180` | 2026-07-10 | fix: DEFAULT companions load even for trivial messages (ping/ok/yes) | null | null |
| `63b75ee` | 2026-07-10 | Fix agency preflight host plugin wiring | null | null |
| `4d17668` | 2026-07-10 | docs: establish linked roadmap worklog and decision system | [AR-08](../roadmap/issue-AR-08-self-contained-documentation.md) | [detail](2026-07-10-4d17668-documentation-system.md) |
| `a896c81` | 2026-07-10 | fix: isolate generated plugin tests from user home | [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md) | [detail](2026-07-10-a896c81-windows-test-isolation.md) |
| `17a62dd` | 2026-07-11 | feat: harden runtime and ship local operations dashboard | [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md), [AR-04](../roadmap/issue-AR-04-runtime-controls.md), [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-10](../roadmap/issue-AR-10-authoritative-runtime-evidence.md), [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-12](../roadmap/issue-AR-12-installed-operations-dashboard.md) | [detail](2026-07-11-17a62dd-production-readiness-refactor.md) |
| `d1275c3` | 2026-07-11 | feat: add optional dashboard service and config parity | [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md) | [detail](2026-07-11-d1275c3-optional-dashboard-service-configuration.md) |
| `afdf8d1` | 2026-07-11 | docs: sync AR-13 tracker mapping | [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md) | null |
<!-- worklog:end -->

## Provenance notes

- `2434f30` contains the name `Hermes` in its historical subject. The subject is retained exactly as committed for faithful provenance; the name does not create an active cross-repository link or dependency.
- `8f6d320` records a handoff document that was later removed. The subject remains part of the immutable commit record; no deleted document was restored for this worklog.
