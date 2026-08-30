---
title: "Worklog detail: Prove exact Codex child activation"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, activation, security, dashboard]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
supersedes: []
superseded_by: null
type: worklog
commit: 77ec4f6
short: 77ec4f6
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Prove exact Codex child activation

## Purpose

Replace the parent-only Codex activation check with a deterministic one-child
probe that can establish current-profile specialist delivery without weakening
hook trust or taking authority from the native scheduler.

## Approach

The canary now plans one bounded work unit and verifies a complete content-free
graph: Codex collaboration JSONL, exact native tool-use identity, immutable
hook-issued grant provenance, child lifecycle, one-use activation consumption,
delegation, model receipt, accepted finalization, response header, platform, and
installed bundle identity. Only current-profile Codex evidence persists the
dedicated proof contract. A recheck clears the prior attestation immediately
before invocation, and CLI evidence reports use atomic replacement.

Schema v38 adds provenance columns, exact validity and immutability triggers,
legacy migration, and an indexed canary routing lookup. The dashboard treats
expired host inspection as unavailable and labels retained evidence as a last
successful or historical proof without exposing a canary action.

## Challenges encountered

An early hook guard denied ambiguous native `spawn_agent` calls and would have
interfered with Codex scheduling. The final design returns no hook decision for
ambiguous or unmatched calls and acts only on positively identified
Agency-owned work. The parser also had to accept monotonic `item.started` to
`item.completed` collaboration evolution without allowing receiver, sender,
prompt, or tool identity conflicts. Adversarial review found both issues before
the checkpoint.

## Decisions and alternatives

The attestation is intentionally a last-successful content-free proof bound to
the recorded host/install identity, not a live configuration probe or a claim
that its discarded evidence graph can be rehashed from inventory. Isolated and
tokenless host diagnostics remain useful but cannot share the strict Codex
activation contract or promote readiness. Persisting a broad latest-attempt
history was deferred; the smaller fail-closed recheck invalidation prevents a
failed attempt from leaving a false current claim.

## Verification

- Documentation metadata, policy availability, worklog generation, and all 455
  maintained Markdown documents passed validation.
- Ruff check and format passed across 584 Python files.
- Exact scheduler and proof tests passed 16 cases in 42.59 seconds.
- Canary and atomic-output tests passed 22 cases in 33.26 seconds.
- New provenance and migration tests passed 11 cases in 5.07 seconds.
- Dashboard server regressions passed, and all 106 UI tests passed.
- No exhaustive Python corpus, compatibility matrix, hosted workflow, or push
  ran.

## Follow-ups

- Install this exact candidate into the current Codex host and run one bounded
  current-profile canary without hook-trust bypass under AR-180.
- A production/release GO still requires the owner-requested manual exhaustive
  workflow at the exact final head and the separate external gates recorded by
  AR-119.
