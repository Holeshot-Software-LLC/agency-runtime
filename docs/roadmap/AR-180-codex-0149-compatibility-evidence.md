---
title: "Codex 0.149.1 native-child compatibility evidence"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [codex, native-child, hooks, compatibility, evidence]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_spawn_provenance.py
supersedes: []
superseded_by: null
---

# Codex 0.149.1 native-child compatibility evidence

## Scope

This is a content-safe compatibility recheck after the local Codex CLI was
upgraded to `0.149.1`. It is not an Agency canary, installation, Rule-4 proof,
or authorization to widen ADR-0159's exact-version attestation profiles.

The probe used existing Codex authentication only through ordinary
`codex exec` calls. It ran no login or logout command, did not inspect or copy
authentication material, and did not change Codex, Agency, Claude, ZCode,
OpenClaw, or Hermes configuration. Agency was not installed for Codex before
or after the probe.

## Content-safe observations

All four fresh parent sessions completed one real depth-one native child. The
raw rollouts remain in the owner-private Codex session store; this repository
retains only their hashes and bounded, content-free projections.

| Parent session | Child session | Spawn message | Marker | Parent rollout SHA-256 |
|---|---|---|---|---|
| `01a03a51-62ca-7b81-95e5-3ce33550e600` | `01a03a51-7195-7722-8c3b-0073af41f76c` | 164 characters, `gAAAA` prefix | absent | `8457c3c4541d2eec3b6db00c49ab455a71e36341a9c6ad4bdbe553a8ddba591f` |
| `01a03a58-4c89-7de1-9d05-cd71784193e1` | `01a03a58-5e0f-7f50-94c1-ed0b7e85652f` | 164 characters, `gAAAA` prefix | absent | `54f8b02137cf2d0f5825c7c395e1307d4368e0620fc3f927092ebf019aa7acbc` |
| `01a03a58-f955-79f2-a1f5-b65ebeca070f` | `01a03a59-0a8a-7521-b825-e7fbc509a742` | 184 characters, `gAAAA` prefix | absent | `83aa56aa513825ee6a96a74aae2317c65ffceca9dcc34329c0291cab97b51461` |
| `01a03a59-6f42-7fa0-8c63-ba93941b50ae` | `01a03a59-8511-71e1-9816-c0f4af33496d` | 184 characters, `gAAAA` prefix | absent | `80338e18a3097e2fe5fa8abd94c731af45fb733f4901f6f3fbe25c45d328581b` |

Every persisted `spawn_agent` call had exactly `fork_turns`, `message`, and
`task_name`. Every message remained Fernet-shaped ciphertext, and none of the
four response items contained `encrypted_function_args`. Each child metadata
record retained the plaintext `thread_spawn.agent_path`, but `agent_role` was
null and no decrypted assignment appeared in the parent call.

The first probe established the current rollout shape. Three changed attempts
then tried to collect a redacted command-hook envelope from a disposable
project. No redacted log was emitted, including after creating a disposable Git
repository and after removing `--ignore-user-config`. Those attempts are
retained as probe-setup failures and were not promoted into hook-schema claims.
They were not retried unchanged.

The current official Codex hook contract independently documents the stable
surface: `spawn_agent` matches `Agent` at `PreToolUse`; that event receives the
local function arguments and may return `updatedInput`; `SubagentStart`
receives `agent_id` and `agent_type` but no task label, parent call ID, or
decrypted assignment. The same documentation calls the rollout transcript an
unstable interface. Source: `https://learn.chatgpt.com/docs/hooks`.

## Stable-hook activation recheck

The installed CLI reports both `hooks` and `multi_agent` as stable features.
Three additional fresh parent sessions then completed one real depth-one child
each while a disposable redacting `PreToolUse` hook was supplied through a
different documented configuration path. The hook retained no assignment
content and was designed to emit only argument keys, message type and length,
ciphertext shape, and whether one fixed harmless marker was visible.

| Hook source | Parent session | Child session | Parent rollout SHA-256 | Redacted hook artifact |
|---|---|---|---|---|
| Project layer plus one-shot trust bypass | `01a03a6f-66b1-79e0-88be-71aff65c91c0` | `01a03a6f-7e7b-79e0-8ca7-4f8ebfcda9b6` | `3a75ab8a4ef4b0034c525afa81ce237a308a2b70cd975f0c64c5807012e13bee` | absent |
| Session `-c` layer plus one-shot trust bypass | `01a03a70-b402-7821-8ec5-f901f91f0e2a` | `01a03a70-ccdd-7f10-8f65-ab9da4745268` | `ebe3be5dc704918b37a3a0ad6395d1008d24e83e7d41177bb50a7d983c5953b6` | absent |
| Named profile plus one-shot trust bypass | `01a03a73-4cbd-7773-9c6b-98d8e0421fbe` | `01a03a73-6a80-7093-a04e-ac34824a658a` | `7676fca949b4b1d0069e0b888927288f56130ceb77208d09127dd5475750befb` | absent |

Every parent rollout again persisted an encrypted `message`; the last two were
228 characters and Fernet-shaped. Codex's streaming JSON omitted the spawn
event, but the canonical parent rollout and each child `thread_spawn` record
correlated the exact depth-one launch. The missing hook artifacts do **not**
prove that `PreToolUse` receives ciphertext: they prove only that no tested
configuration produced an observable hook invocation. A hook-engine sanity
probe that matches every local tool remains the next bounded discriminator.

## Configuration invariants

The persistent Codex configuration SHA-256 was
`f593344782256a0f6d5346b6e132893a030ae325fea2152fb49484011a04a5a8`
before and after. The effective Agency configuration SHA-256 was
`8cebe127352000a7e8a238e7fa842f428f985721a4d58fc3f1b5e2ffb8fe354b`
before and after. No secret value was read, printed, copied, or retained.

## Verdict

Codex `0.149.1` does not remove the blocker. Agency still cannot infer a child
specialist from the encrypted assignment or bind `SubagentStart` context to the
exact parent call through a documented authenticated field. The exact
`0.147.0` attestation profiles therefore remain unchanged, and `0.149.1` must
fail open with an explicitly unstaffed native child. Installed and Live remain
unproven, and no AR-119 matrix cell moves. The documented `PreToolUse` rewrite
surface is a plausible future integration path, but it is not current runtime
evidence until a live hook invocation is observed and causally bound.
