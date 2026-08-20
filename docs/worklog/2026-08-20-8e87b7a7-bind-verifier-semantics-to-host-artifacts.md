---
title: "Worklog detail: bind verifier semantics to host artifacts"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [workforce, acceptance, evidence, native-child]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
supersedes: []
superseded_by: null
type: worklog
commit: 8e87b7a7a612fd75acf43cbeed7fd1e7bc5daec8
short: 8e87b7a7
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: bind verifier semantics to host artifacts

## Purpose

Retire the flat accepted-outcome verdict, which could imply that a verifier
authored a producer transcript digest the verifier cannot read. Encode the
AR-252 joint-verdict ruling directly in the evaluated envelope and persisted
manifest before any live producer/verifier collector is built.

## Approach

`agency.accepted-outcome.v2` separates the verifier-authored semantic half from
the collector-authored binding half. Semantics are bound to the verifier's
host-artifact digest and bounded record index; binding names the producer
artifact digest and verifier child. Both identities participate in the replay
key, and read-back rejects a manifest if any attribution field changes.

Tests now construct both host proofs with artifact digests and exercise the v2
shape through the evaluator, Store recorder, readiness calculation, automatic
promotion, workforce lifecycle, and dashboard projection.

## Challenges encountered

The first widened run exposed one fixture that replaced a verifier proof
without preserving its artifact digest. The implementation correctly reported
the earlier missing-digest refusal; the fixture was repaired to reach its
intended shared-specialist assertion. Local pytest and Ruff also required their
normal attested cache/temp roots because the sibling worktree sandbox disallows
those writes.

## Decisions and alternatives

The former v1 schema is refused rather than interpreted compatibly, because
compatibility would preserve the authority ambiguity this change removes. No
production collector emitted v1 envelopes, so there is no live acceptance
history to migrate. A separable produced-work digest remains a future tightening
if host contracts provide one.

The one-use verified-delivery capability was not widened. Exactly two
consumptions inside one atomic pairing transaction remain an owner-controlled
threat-model decision, not an incidental part of this schema change.

## Verification

- `261 passed` across accepted outcomes, workforce promotion, dashboard, and
  workforce lifecycle tests with warnings treated as errors.
- Ruff check and format check passed for all changed Python files.
- Documentation metadata and policy-availability checks passed.
- `git diff --check` passed.

## Follow-ups

- Obtain the AR-252 capability-seal ruling before building the live pairing
  collector.
- After that collector is locally sealed, obtain fresh install/live-draw
  authorization and prove Claude accepted outcomes and automatic promotion.
- Keep the later ZCode plural-card/outcome package separate.
