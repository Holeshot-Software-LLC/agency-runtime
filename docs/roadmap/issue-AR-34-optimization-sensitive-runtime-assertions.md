---
title: "AR-34: Replace optimization-sensitive runtime assertions"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [runtime, assertions, canary, evaluation, security]
related:
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-34
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/35"
depends_on: []
blocks: []
---

# AR-34: Replace optimization-sensitive runtime assertions

## Problem

Production canary, host parsing, and delegation evaluation paths use Python
`assert` statements for correctness checks. `python -O` removes those checks,
which can turn invalid or incomplete evidence into crashes or false-positive
evaluation results.

## Current state

The normal warning-strict suite exercises the asserted conditions, but it does
not prove behavior after the interpreter strips assertions. Security scanning
identified the production assertions during the final hardening pass.

## Approach

Replace every production-package assertion with an explicit, typed fail-closed
check and stable diagnostic. Keep canary evidence unavailable when prerequisites
are absent, reject malformed host-parser results, and make the delegation eval
raise independently of interpreter optimization. Exercise the same failure
contracts through a real optimized child interpreter.

## Dependencies

This is a test-safety and runtime-integrity correction within the existing
canary and evidence boundaries. It requires no new architectural decision.

## Acceptance

- [x] No production package module relies on `assert` for runtime correctness.
- [x] Canary and host parsing fail closed on missing or malformed state.
- [x] Delegation evaluation cannot silently pass under `python -O`.
- [x] Warning-strict, exact-coverage, Windows/Linux, package, and tracker gates pass.
