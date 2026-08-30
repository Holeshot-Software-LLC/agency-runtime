---
title: "Worklog detail: Isolated Codex canary boundary"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, activation, evidence, production-readiness]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
supersedes: []
superseded_by: null
type: worklog
commit: 29fd9a9beaa21f2276e4e6b5f7e16bb83ba9b690
short: 29fd9a9
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Isolated Codex canary boundary

## Purpose

Preserve the sole isolated-profile attempt from exact packaged candidate
`1a58e5e` without reclassifying it as activation evidence or repeating a mode
that cannot admit the deterministic current-profile fixture.

## Approach

Telemetry immediately preceded one 120-second-bounded canary from the fresh
wheel. Its content-free report was written outside the repository and reduced
to exact route, collaboration, activation, cleanup, size, and digest evidence.
The failed run was closed by exact request fingerprint, and the result was added
to AR-180 and the AR-119 recovery records.

## Challenges encountered

Isolated Agency mode intentionally used ordinary semantic planning. It selected
two units (`finops-engineer` and `code-reviewer`) rather than the one-unit
current-profile fixture, so the exact-one-child verifier accepted no
collaboration. This attempt therefore could not exercise the new persisted
parent/child parser.

## Decisions and alternatives

No retry, planner tuning, relaxed topology, fabricated activation, or isolated
attestation was used. The result establishes a test-surface boundary: only the
existing-Store current-profile contract admits the nonce-bound deterministic
fixture, and only that attended path can close AR-180.

## Verification

- Trace `019fa6c9-1e2d-7021-acdd-5a4b08113f85` recorded one accepted route with
  exactly two planned units and two suggested delegations.
- Invocation status was failed with exit code 1, no accepted collaboration, no
  activation grant/consumption, no specialist load, no worker run, no valid
  header, and no attestation.
- Failed-run cleanup closed its one exact candidate run.
- The 12,614-byte content-free report has SHA-256
  `65981b64cb441e550bcc949ed5dfbdd37c8c7a3201c062091d3215a36c1fae95`.
- No trusted-install mutation, retry, hosted workflow, exhaustive diagnostic,
  push, tag, or publication occurred.

## Follow-ups

After the operator returns, install exact candidate `1a58e5e`, trust the changed
eight-hook inventory, and run one current-profile activation verification. Do
not repeat the isolated semantic-planner attempt as a substitute.
