---
title: "AR-192: Fail fast on Codex hook trust drift"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [codex, hooks, trust, activation, performance]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_hook_trust.py
  - tests/test_codex_hook_trust.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-192
priority: p0
tracker_url: null
depends_on: [AR-182]
blocks: [AR-180]
---

# AR-192: Fail fast on Codex hook trust drift

## Problem

An attended Codex refresh can replace Agency's hook commands while an older
Codex TUI still holds the pre-refresh hook snapshot. Approving that stale view
writes valid trust hashes for the prior definitions, but the settled plugin is
correctly reported as `modified` and none of its hooks execute. Activation
verification nevertheless spent a full model-backed canary before discovering
that the Store had received no hook evidence.

This failure has recurred during rapid upgrade testing. Codex's refusal to run a
modified command is the intended security boundary; the Agency verifier's
failure to inspect that boundary before a model call is the bug.

## Current state

Codex 0.145's read-only app-server `hooks/list` method is the authoritative
inspection surface. A fresh inspection of installed plugin
`0.1.0+codex.9e970ea1b470` found all eight expected Agency hooks enabled but
`modified`. Their current hashes differed from the hashes persisted by the
stale TUI. The same result held for the repository and private canary working
directories, ruling out project trust and canary CWD as the cause. Tracker
creation remains pending explicit authorization for the outward-facing write.

The implementation now binds an isolated worker and the selected Codex
executable to frozen, revalidated artifact identities, bounds the interactive
protocol and JSON structure, and projects only allowlisted trust evidence. Two
independent read-only reviews found no remaining scoped Critical, High, or
Medium issue. Seventy focused trust, activation, CLI-projection, and
fail-before-model tests pass; the 536-test named production spine, 109 dashboard
tests, documentation checks, lint/format, and routing evaluation also pass.

## Approach

Before any current-profile Agency canary invokes a model, ask the selected
Codex executable for `hooks/list` in the exact canary working directory. Select
only the `agency-preflight@agency-runtime` plugin, require the canonical AR-182
event inventory exactly once, and require every entry to be enabled and
`trusted`. Bound process time and output, return only sanitized event, status,
and hash evidence, and never write Codex configuration or reproduce its private
hash algorithm. Fail closed with a precise remediation when inspection is
unavailable, incomplete, disabled, untrusted, or modified.

## Dependencies

AR-182 owns the canonical eight-event inventory. AR-180 owns the final live
activation proof, and AR-191 owns the current V2 hook identity. ADR-0077 keeps
Codex trust owner-approved and forbids bypassing or privately mutating it.

## Acceptance

- [x] Current-profile Agency verification performs `hooks/list` before any
  model-backed Codex execution.
- [x] The preflight requires the exact canonical Agency event inventory and
  rejects missing, duplicate, disabled, untrusted, or modified entries.
- [x] The inspection is read-only, bounded, fail-closed, and omits hook command
  strings from returned evidence.
- [x] A trust failure returns actionable structured evidence in seconds and
  does not start the expensive canary.
- [x] Focused trust and canary tests plus the named fast production spine pass.
- [ ] After an exact reinstall, one fresh TUI approval is confirmed by an
  authoritative 8/8 trusted inspection before the live canary.
