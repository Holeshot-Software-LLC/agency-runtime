---
title: "Worklog detail: Record exact Codex activation recheck"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, installation, evidence, production-readiness]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
supersedes: []
superseded_by: null
type: worklog
commit: 54d82a9
short: 54d82a9
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Record exact Codex activation recheck

## Purpose

Preserve the first exact installed-candidate outcome without upgrading a
registered plugin or a zero-evidence model response into activation proof.

## Approach

Exact ledger head `af892ae` was materialized in an owner-private detached
worktree, built with an owner-private interpreter, independently verified, and
fresh-installed from its canonical Windows wheel. The attended installer then
verified Windows operator presence, atomically backed up and replaced the
existing plugin, refreshed native registration, and proved its postconditions.
One current-profile canary ran with the strict confirmation and a 180-second
ceiling; its content-free report was atomically persisted and hashed.

## Challenges encountered

The first source-tree installer and builder attempts failed before mutation
because the workspace and its original interpreter permit cross-account
substitution. Those failures were retained as correct security evidence. The
private packaged path succeeded. The live canary then completed normally but
reported no hook route or header. Hook approval occurred before this exact
bundle refresh, but Codex exposes no supported trust-state read API, so renewed
trust is recorded as the next gate rather than asserted as the proven cause.

## Decisions and alternatives

No hook-trust bypass, private state edit, automatic approval, or blind retry was
used. The canary outcome remains a failure and no attestation exists. A second
attempt is deferred until the operator approves the exact refreshed hook set in
the supported terminal TUI.

## Verification

- Canonical Windows build passed for exact head `af892ae`; independent artifact
  verification passed.
- Fresh Python 3.13 wheel install and packaged verifier loading passed.
- Windows operator presence, atomic refresh, native remove/add, and installation
  postconditions passed in 182.5 seconds.
- The sole current-profile canary completed in 36.9 seconds and failed
  `route_not_found` with all proof cardinalities zero; evidence SHA-256 is
  `b5bb99e1b430065769eda3c960a829927546dd5c81a266cf6ba6295276344750`.
- No exhaustive suite, compatibility matrix, hosted workflow, retry, or push
  ran.

## Follow-ups

- Renew terminal-TUI hook trust for `0.1.0+codex.92db70112a1a`, then perform one
  bounded current-profile recheck under AR-180.
- Production remains NO-GO until that proof and the independent AR-119 release
  gates are complete.
