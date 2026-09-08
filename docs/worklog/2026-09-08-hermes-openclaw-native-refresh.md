---
title: "Hermes and OpenClaw native refresh"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [hermes, openclaw, native, verification]
pr: null
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/worklog/2026-09-08-trusted-native-acceptance.md
supersedes: []
superseded_by: null
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Hermes and OpenClaw native refresh

## Outcome and scope

Owner approved refreshing Hermes, then OpenClaw with its normal gateway
stop/update/restart workflow, followed by one ordinary native turn per host.
Check actual staffing, injection, truthful headers and terminal finalization.
Source baseline is clean main24b50cb8. AR-414/415 completion proves Codex only;
AR-404 remains open. No broad backlog, Windows or credential changes.

## Installed checkpoint

Both hosts initially report registered/enabled, loaded unknown, no attestation,
and published projection4d2934ddb59e behind installed source6e7dc299c23e.
Hermes normal `agency install --agent hermes --no-dashboard --json` succeeds
at2026-09-08T19:53:11Z. Plugin enabled and listed by native CLI, hook budget read
succeeds. Bundlebdce2726fd101e572287ba5ebc9c938f8ac66a3d39f6065222d9a5e3a78f2ea9;
backup identifier20260908T195311.634794Z. Runtime remains unverified until fresh
native execution. No dashboard start or existing Hermes process termination.

## Verification

Existing same-source checks immediately precede this package: focused108pass,
production1151pass/3skip, UI224pass, Ruff and routing pass; frozen-source
conformance188/188pass. Production/test/script diff from source8629e2ed is empty.
All614installed files match the verified wheel. This package changes host
integration and records, not Python defaults. Native evidence follows; installer
success is not native proof. No exhaustive corpus or cross-platform claim.

## Follow-ups

Run fresh Hermes and OpenClaw native turns after their normal refresh; inspect
exact failures rather than retrying for approval. Preserve operator files and
restore OpenClaw gateway service after the approved maintenance window.
