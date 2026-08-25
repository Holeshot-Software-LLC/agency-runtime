---
title: "Worklog detail: Isolate Codex 0.149 spawn hook gap"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [codex, hooks, native-child, compatibility, evidence]
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
commit: 04a23ebe
short: 04a23ebe
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
---

# Worklog detail: Isolate Codex 0.149 spawn hook gap

## Purpose

Separate general Codex hook activation from the missing `spawn_agent`
`PreToolUse` artifact before changing any Agency behavior.

## Approach

Replaced the disposable profile's narrow matcher with a match-all matcher and
ran one bounded read-only `pwd` command. The hook retained only the tool name,
input key set, absent-message shape, and fixed-marker absence. The profile and
capture script were removed or preserved outside the repository after use.

## Challenges encountered

`codex doctor` rejects runtime profiles before inspecting them, so it provided
no hook inventory. The changed runtime probe succeeded: Codex ran one Bash
tool, and the same named profile, trust bypass, and script that had produced no
spawn record emitted the expected one-line `PreToolUse` projection.

## Decisions and alternatives

Treat the prior missing captures as a spawn-specific matcher or specialized
dispatch gap, not a general hook-engine failure and not proof of ciphertext
hook input. Keep 0.149.1 unstaffed until a match-all native-child probe either
captures the assignment or confirms the specialized path does not dispatch.

## Verification

- Parent session `01a03a79-2964-7340-ab3b-64632fbf5062` completed exactly one
  read-only Bash command.
- Parent rollout SHA-256 is
  `94693316c336ff68a94af7efd677b35c009347fbf59b7f01f3c8693314ec7c05`;
  redacted capture SHA-256 is
  `6a52deca6c8f644a2452b24bddf3dbfc3fd988ad407226140e2e1fc9790f06aa`.
- Documentation metadata, policy availability, worklog consistency, link and
  schema validation, and `git diff --check` passed for 809 Markdown files.
- Persistent Codex configuration remained byte-identical.

## Follow-ups

Run one changed native child through the same match-all profile. If it produces
no hook event while Bash does, retain the fail-open boundary and report the
documented-versus-observed host dispatch gap without weakening Agency.
