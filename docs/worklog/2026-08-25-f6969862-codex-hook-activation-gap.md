---
title: "Worklog detail: Record Codex 0.149 hook activation gap"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [codex, native-child, hooks, compatibility, evidence]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-180-codex-0149-compatibility-evidence.md
  - docs/roadmap/handoffs/issue-AR-180.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: f6969862
short: f6969862
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
---

# Worklog detail: Record Codex 0.149 hook activation gap

## Purpose

Determine whether Codex CLI 0.149.1's documented stable hooks expose a safe
plaintext native-child assignment surface without changing the proven Codex
OAuth/configuration boundary or running an Agency canary.

## Approach

Confirmed locally that `hooks` and `multi_agent` are stable features and used
the official hook contract to build a disposable redacting `PreToolUse` probe.
The probe was supplied through project, session `-c`, and named-profile layers,
each with the documented one-shot trust bypass. Each changed request completed
one real depth-one child. Only content-free parent/child identities, argument
keys, ciphertext shape and length, artifact hashes, and capture presence were
retained.

## Challenges encountered

Codex's streaming JSON omitted each spawn event and showed an empty wait target,
even though the canonical parent rollout and child `thread_spawn` metadata
proved the launch. None of the three hook sources emitted the redacted capture.
That absence cannot establish whether hook input would be plaintext or
ciphertext; it remains an activation/dispatch gap. An initial documentation
policy check also used a system interpreter without the checkout import path;
the changed trusted-interpreter invocation passed.

## Decisions and alternatives

Do not broaden the exact 0.147 transcript attestor or install Agency into Codex
based on documentation alone. Keep 0.149.1 fail-open and explicitly unstaffed.
Retain `PreToolUse` as a plausible Codex-only integration surface, but require a
live content-safe hook envelope and exact causal binding before implementation.
Do not restore AR-209's retired plan-row transport or infer a specialist from a
plaintext task label.

## Verification

- Documentation metadata and link/schema verification passed for 808 Markdown
  files; policy availability, worklog consistency, and `git diff --check`
  passed.
- The preceding compatibility checkpoint passed 382 focused tests, the named
  856-test fast spine with 3 skips, 134 dashboard tests, Ruff lint/format,
  routing evaluation, and decision conformance with every curated mutation
  killed and source unchanged.
- Persistent Codex and Agency configuration hashes remained byte-identical.

## Follow-ups

Run one disposable match-all hook with a harmless read-only local tool to
separate basic hook-engine activation from `spawn_agent` specialized dispatch.
Only if that fires should a changed child marker test and focused Agency
implementation begin.
