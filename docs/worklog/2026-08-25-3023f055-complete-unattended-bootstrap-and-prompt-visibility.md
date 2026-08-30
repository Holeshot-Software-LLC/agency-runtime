---
title: "Worklog detail: Complete unattended bootstrap and prompt visibility"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [containers, installation, codex, workforce, dashboard, observability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 3023f0557e72911c4d42be53dccca3369b05ca8e
short: 3023f055
date: 2026-08-25
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/326
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
---

# Worklog detail: Complete unattended bootstrap and prompt visibility

## Purpose

Make one explicit Agency installation transaction sufficient for a dedicated,
unattended Codex, Claude Code, or OpenClaw container, and give operators full
CLI/dashboard visibility into the governed prompt of every durable workforce
member without confusing stored definitions with host delivery.

## Approach

Add exact install-config binding and a fail-closed `--production-container`
mode. Codex receives an Agency-owned managed-only system hook policy plus a
mandatory normal-invocation canary; prior activation proof is cleared before
policy mutation. Read-only inspection validates the owned TOML and relay
without executing either and projects managed-policy authority separately from
activation proof. A new workforce Store reader exposes current or exact
historical prompt content across every standing, with CLI and authenticated
dashboard detail surfaces carrying provenance and delivery-proof disclaimers.

## Challenges encountered

The first response-budget regression used an intentionally incomplete worker
fixture that the richer detail path correctly rejected before serialization;
the fixture now preserves the real detail contract. Managed-policy inspection
also exposed Windows newline translation in a test rewrite, so the test now
uses the same atomic writer as production. The combined dashboard measured
386,366 bytes, 318 bytes above the prior audited ceiling; the bound moved only
to 378 KiB, leaving 706 bytes (0.18 percent) of headroom.

## Decisions and alternatives

ADR-0173 supersedes the claim that an invocation-scoped trust bypass can serve
as production bootstrap. Undocumented Codex trust-store writes, automatic
enterprise-policy merging, shared-workstation managed-only hooks, and letting
Conveyor finish setup were rejected. Prompt bodies remain explicit detail
lookups rather than collection fields, and stored content never stands in for
correlated host-written delivery evidence.

## Verification

- The final managed-policy, install CLI, doctor, packaging, and dashboard
  regression command passes 201 tests.
- All 138 dashboard UI tests pass, including managed authority and complete
  prompt rendering.
- Repository-wide Ruff passes and all 695 Python files satisfy format checks.
- Documentation metadata, policy, worklog, graph, and diff validation pass.
- The exact 386,366-byte dashboard passes below the audited 378 KiB ceiling.

## Follow-ups

Install this checkpoint on Windows for authenticated prompt/authority visual
inspection and ordinary diagnostics. Then prove the production transaction in
clean Linux Codex, Claude Code, and OpenClaw containers and update AR-297. The
tracker mapping remains pending explicit authorization.
