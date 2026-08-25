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
unproven, and no AR-119 matrix cell moves.
