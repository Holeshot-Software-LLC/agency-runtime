---
title: "Exact installed uv-plan evidence for AR-190"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [updates, uv, evidence, isolation]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
supersedes: []
superseded_by: null
type: worklog
commit: d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f
short: d1a9260c
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
---

# Worklog detail: docs(roadmap): capture exact installed uv-plan evidence for AR-190

## Purpose

Supply the previously missing real installed uv-tool plan evidence for the
existing AR-190 implementation, without changing the owner's installation.

## Approach

Build and independently verify a portable wheel from clean detached
`c64ce3ce54c6e51280292298b5e3600611cb72fc` under `umask 077`. In an existing
exact local Docker image, let verified uv 0.11.8 create its legitimate default
tool installation and receipt. Invoke that installed Agency entrypoint to
resolve the same exact immutable SHA, without executing either printed command.
Preserve exact raw JSON and readable portable evidence. The later record-only
candidate has identical runtime, scripts, tests and packaging configuration;
the receipt does not claim its additional documentation was live-executed.

## Challenges encountered

An earlier bubblewrap capability probe failed at uid-map setup; no install
or plan ran there. The separately authorized local-container route succeeded.
The first container used an older exact artifact, so a fresh same-SHA artifact
was built and the bounded plan repeated. Both successes and the original
failure are retained. The pre-existing c64ce3ce merge-ledger omission was
resolved by fast-forwarding its already-created `d28ccc23` ledger commit.

## Decisions and alternatives

Apply existing ADR-0107's planning/application separation. Do not relabel the
owner's non-uv AR-348 venv, synthesize a uv receipt, install uv into the owner
environment, override tool target directories or execute an upgrade. No new
authority or architectural decision was introduced.

## Verification

Canonical builder, strict Twine and independent portable verifier exit zero.
The actual installed plan selects `uv-tool` with no pip installed; 669 compared
prefix files, the uv receipt and Agency entrypoint are unchanged after the
plan. Both disposable containers are removed and owner wrapper/input hashes
are unchanged. Focused update/CLI tests: 67 passed in 0.83 seconds. Targeted
Ruff, documentation, metadata, policy-availability, worklog and diff checks
pass at the evidence checkpoint. Isolated acceptance is not yet claimed.

## Follow-ups

Freeze the AR-190 builder at this committed evidence candidate and run the five
isolated verifiers. Parent serializes PR publication and merging; no owner
upgrade or native host activation is part of this plan-only completion.
