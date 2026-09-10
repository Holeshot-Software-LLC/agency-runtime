---
title: "Ground Hermes nominations in actual unit scope"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [hermes, workforce, reliability]
related:
  - docs/roadmap/issue-AR-429-ground-recruiter-specialties-in-unit-scope.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-429-ground-recruiter-specialties-in-unit-scope.md
---

# Ground Hermes nominations in actual unit scope

## Purpose

Continue the next bounded Hermes package after AR-428 and AR-423 merged. Preserve
OpenClaw, Codex and Claude evidence scopes and defer Zcode implementation.

## Approach

The captured critic packet shows required type-design and silent-failure roles
on ordinary arithmetic analysis, plus an additional silent-failure role on the
static review. These were recruiter-required nominations, not deterministic
coverage additions. The available correctness reviewer and full selected
contracts support investigating semantic nomination relevance; the critic's
single code cannot attribute a sole cause. Both recruiter prompts now share a
unit-scope grounding instruction for leads and additional teammates, with
positive specialized cases and typed-coverage exceptions kept explicit.

## Challenges encountered

Broader focused checks240 passed/1skipped with2 foundation failures; unchanged
main reproduces both. AR-430/#835 defers those domain-coverage fixtures under
ADR-0217. This prompt change cannot affect their deterministic code path.

The rejected receipt omits the plan after failure. Use the already captured
actual critic request and response, not reconstructed success. Recipe21 native
adoption and end-to-end outcome are pending; no failed receipt is reopened.

## Decisions and alternatives

This implements existing inference ownership and ADR-0200 semantic criticism.
No new staffing authority or architectural decision is introduced. Reject
per-specialist bans, manual selection, critic relaxation and retries without a
new bounded evidentiary reason. Prompt tests prove delivery, not model behavior.

## Verification

Bounded focused217/1skipped, named production1151/3skipped, UI224 and routing
passed. Ruff788 and documentation checks passed before deferred AR-430 filing.
Frozen conformance is running; native proof follows the source checkpoint. No exhaustive or Windows workflow requested.

## Follow-ups

AR-429 native/isolated acceptance remains pending. AR-418 retains actual-checkout
upstream adoption and original truncation-cap evidence. AR-404 stays open.
