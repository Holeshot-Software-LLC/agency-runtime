---
title: "Worklog detail: Preserve durable hosted runtime authority"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [ci, portability, windows, linux, security, node]
related:
  - docs/roadmap/README.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
supersedes: []
superseded_by: null
type: worklog
commit: 0c41fbdf88c9127424de02ccccec7aa193c24f00
short: 0c41fbd
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Preserve durable hosted runtime authority

## Purpose

Close the final Linux and Windows portability defects revealed by PR #104's
hosted matrix while preserving the production executable and storage trust
contracts.

## Approach

Test-environment isolation now treats `AGENCY_CI_*` values as reserved runtime
authority receipts rather than product configuration. Doctor smoke tests retain
the hash-verified private Node mirror prepared by the workflow, while tests that
specifically model an unavailable Node executable remove that receipt
explicitly.

Windows CI root selection now checks the complete profile namespace before
choosing a persistent root. When the runner profile is replaceable, it walks to
the nearest already-trusted ancestor and derives a deterministic 128-bit root
name from the current user SID and canonical requested path. The existing
atomic protected-DACL bootstrap still creates and verifies the selected root;
generic production path validation is unchanged.

## Challenges encountered

The Linux failure looked like a production executable rejection, but the
workflow had already created the correct private Node copy. An autouse fixture
then erased its authority receipt and silently selected the shared tool cache.

On Windows, an owner-private child below an untrusted runner profile was safe
only while the creating process held an in-memory directory guard. Later test
processes could not reconstruct that authority. The durable path therefore had
to exclude the rejected profile component rather than weakening its ACL
classification.

## Decisions and alternatives

Rejected alternatives included trusting hosted tool-cache executables, treating
CI environment flags as security authority, relaxing ancestor validation, or
persisting a process-local guard as if it were cross-process evidence. The
selected design uses existing OS identity and ACL evidence and fails closed when
no writable trusted Windows ancestor exists.

## Verification

- Affected doctor, config, and configuration suites: 149 passed and 1 skipped.
- Windows relocation security probe: direct, relocated, deterministic,
  identity-separated, and fail-closed paths passed.
- Ruff, formatting, Python compilation, and whitespace checks passed.
- Two independent reviews found no actionable security or correctness defect.

## Follow-ups

Run the complete hosted matrix. AR-104 remains in progress until every Windows,
Linux, coverage, performance, dashboard, security, build, and artifact job is
green.
