---
title: "Worklog detail: Close Codex 0.149 hook compatibility probe"
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
commit: 53350797
short: 53350797
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
---

# Worklog detail: Close Codex 0.149 hook compatibility probe

## Purpose

Settle whether Codex CLI 0.149.1 exposes plaintext native-child assignment at
its documented `PreToolUse` boundary and apply any narrow Agency compatibility
repair actually justified by live evidence.

## Approach

Used the same disposable match-all profile that had captured a harmless Bash
call to run one genuinely changed depth-one child marker. Retained only the
redacted hook projection, exact parent/child identities, and artifact hashes.
Then compared the observed canonical tool name with Agency's checked-in Codex
matcher and normalization allowlists.

## Challenges encountered

Codex streaming output again omitted the spawn event and showed an empty wait
receiver set; canonical parent and child rollouts proved the real launch. The
hook nevertheless emitted both local function events, resolving the ambiguity:
the spawn tool name is `collaborationspawn_agent`, and its assignment is already
Fernet ciphertext before `PreToolUse` runs.

## Decisions and alternatives

No Agency installer or adapter repair is warranted. Agency already matches and
normalizes `collaborationspawn_agent`; changing the matcher would be redundant,
while selecting from `task_name` or weakening authenticated staffing would be
unsafe. Keep Codex 0.149.1 children native but explicitly unstaffed. Revisit
only when a future host release exposes authenticated plaintext or an exact
causal binding.

## Verification

- Parent `01a03a7c-3667-72f2-8c49-1d5a0145fa8e` launched depth-one child
  `01a03a7c-51f2-74d3-a4c6-c8abbda4d006`.
- Parent rollout SHA-256 is
  `9d75a7c7a408b3f518fd72ea87c7afcc6c6b40ea075d40f13352b07caeb12df4`;
  two-line redacted capture SHA-256 is
  `da650efeb5d47187733baf8595b6d54821e411420518fcb6220af4b07123f756`.
- Spawn input contained exact keys `fork_turns`, `message`, and `task_name`;
  `message` was a 228-character Fernet string, the fixed plaintext marker and
  `encrypted_function_args` were both absent.
- Documentation metadata, policy availability, worklog consistency, link and
  schema verification, and `git diff --check` passed for 810 Markdown files.
- Persistent Codex and Agency configuration hashes remained byte-identical;
  every disposable hook/profile file was removed after evidence capture.

## Follow-ups

No further 0.149.1 probe is justified. AR-180 and AR-255 remain open for a
future authenticated host surface and eventual Installed/Live/Rule-4 proof;
this compatibility package advances no matrix cell.
