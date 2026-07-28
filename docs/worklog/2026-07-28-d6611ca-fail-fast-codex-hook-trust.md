---
title: "Worklog detail: Fail fast on stale Codex hook trust"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [codex, hooks, trust, activation, security, performance]
related:
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: d6611caabfb34708cb2c4ed65d3839e53b1119de
short: d6611ca
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: Fail fast on stale Codex hook trust

## Purpose

Prevent current-profile activation verification from spending a model-backed
canary when Codex already reports that the installed Agency hooks are missing,
disabled, untrusted, or changed. This closes the recurring stale-TUI failure in
which approval covered the pre-refresh definitions while all settled hooks were
correctly classified `modified` and therefore never executed.

## Approach

A strongly contained isolated worker now performs Codex app-server
`initialize` followed by read-only `hooks/list` in the exact canary working
directory. It selects only `agency-preflight@agency-runtime`, derives the eight
expected event names from the canonical installer inventory, and requires each
exactly once, enabled, owner-trusted, and hash-valid. Executable and bootstrap
artifacts are frozen and revalidated; protocol time, lines, bytes, JSON depth,
and nodes are bounded. Only allowlisted counts plus event, status, and hash
evidence cross the boundary. The canary, proof, and CLI projections sanitize
that report independently and record `model_invocation_attempted=false` on a
trust failure.

## Challenges encountered

Codex app-server requires an interactive initialize sequence; closing stdin
after a prefilled one-shot request disconnects before `hooks/list` can return.
The worker therefore owns the short exchange while the existing process
boundary owns timeout and tree cleanup. Independent reviews also found and
closed sparse forged-trust acceptance, managed-hook ambiguity, response-ID
type confusion, unhashable malformed fields, CLI evidence loss, and raw-report
pass-through. A source checkout intentionally fails the outer executable
namespace policy on this Windows volume, so the exact installed package remains
the required end-to-end transport proof.

## Decisions and alternatives

Codex remains the authority for hook trust. Agency does not write Codex
configuration, reproduce private hash logic, or use the trust bypass in a
current profile. Managed trust was not accepted as a substitute for the exact
fresh owner approval required by ADR-0077. A general interactive process API
was rejected for this bounded need; the small worker reuses the hardened
one-shot containment boundary without expanding product process authority.

## Verification

- Seventy focused trust, activation, CLI projection, redaction, malformed-input,
  and fail-before-model tests passed in 3.64 seconds.
- The final named warning-strict production spine passed 536 tests with 5
  platform skips in 77.07 seconds.
- All 109 dashboard UI tests and every routing, policy, delegation,
  performance, retrieval-scale, and CLI-startup gate passed.
- Ruff lint/format, metadata, policy, worklog, documentation, and diff checks
  passed for the final source candidate.
- A direct read-only installed-Codex protocol probe returned the exact eight
  enabled `modified` hooks in 1.2 seconds without a model invocation.
- Two independent read-only reviews found no remaining scoped Critical, High,
  or Medium blocker. No exhaustive suite or hosted workflow ran.

## Follow-ups

Install the exact clean checkpoint, close pre-install Codex TUIs, approve the
settled eight definitions once from a fresh TUI, require an authoritative 8/8
trusted inspection, and run one bounded current-profile canary under AR-192 and
AR-180. Tracker creation remains pending explicit outward-write authorization.
