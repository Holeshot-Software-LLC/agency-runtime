---
title: "AR-180 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [handoff, codex, native-child, hooks, compatibility]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-180-codex-0149-compatibility-evidence.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/worklog/2026-08-25-cc41b21f-codex-0149-opaque-compatibility.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-180
branch: codex/ar180-codex-0149-subagent-context
evidence_commit: cc41b21f2dd8cad5911d43ffe4bf7ba76924786b
minimum_ledger_commit: 17b27b8cf3ff49078ff840bc7fd43c65f5846cad
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-180 active recovery capsule

## checkpoint

- Worktree `/tmp/agency-runtime-ar180-codex-0149.HK2zvZ` is on branch
  `codex/ar180-codex-0149-subagent-context`, based on current `origin/main`
  `04057072`.
- The latest complete substantive/ledger pair is `cc41b21f` / `17b27b8c`.
  The branch is clean apart from ignored disposable hook-probe files.
- Codex CLI is `0.149.1`. Agency was not installed into Codex and no Agency
  canary, login, logout, OAuth reconfiguration, or host configuration change
  was performed.
- Persistent Codex config SHA-256 remains
  `f593344782256a0f6d5346b6e132893a030ae325fea2152fb49484011a04a5a8`;
  effective Agency config SHA-256 remains
  `8cebe127352000a7e8a238e7fa842f428f985721a4d58fc3f1b5e2ffb8fe354b`.

## completed-evidence

- Four initial fresh depth-one children persisted only `fork_turns`, encrypted
  `message`, and `task_name`; none exposed `encrypted_function_args`.
- Three additional fresh depth-one children tested project, session `-c`, and
  named-profile `PreToolUse` hook sources with the one-shot trust bypass. All
  parent messages remained encrypted and no redacted hook artifact appeared.
- The installed feature inventory calls hooks and multi-agent stable. Official
  docs say `spawn_agent` matches `Agent` at `PreToolUse` and supports argument
  rewrite, while `SubagentStart` lacks assignment and parent-call identity.
- The missing hook artifact is an activation gap, not evidence that live hook
  input is encrypted. No exact 0.149 attestation profile was added.
- Focused verification passed 382 tests. The named fast spine passed 856 with
  3 skips, dashboard UI passed 134, routing passed, and decision conformance
  passed with its baseline green, every curated mutation killed, and source
  unchanged. Documentation and Ruff gates passed before this checkpoint.

## exact-blocker

No tested 0.149.1 hook source has emitted an observable `PreToolUse` envelope.
Without that envelope, Agency cannot prove it sees plaintext assignment input
or bind a staffing rewrite to the exact native spawn. Persisted rollouts remain
encrypted, and `SubagentStart` is insufficient by itself.

## same-task-continuity

Continue in this task after the required clean checkpoint. Do not start a new
task or transfer ownership because the telemetry threshold was crossed.

## next-bounded-work-package

1. Use a disposable named profile whose `PreToolUse` matcher accepts every
   local tool and run one harmless read-only shell tool to prove or disprove
   basic hook-engine activation.
2. If the sanity hook fires, run one changed native-child marker and inspect
   only the bounded redacted projection. Diagnose matcher or specialized-tool
   dispatch before changing Agency.
3. If plaintext is observed, add a regression first and design the smallest
   authenticated Codex-only pre-spawn rewrite. If it is not, retain unstaffed
   fail-open behavior and close this compatibility package.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused Codex hook/provenance tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Do not install Agency into Codex, run an Agency Codex canary, or alter Codex
  OAuth/config while testing the new host surface.
- Do not widen exact 0.147 transcript attestation to 0.149 based on similar
  ciphertext shape or undocumented behavior.
- Do not restore AR-209 plan-row transport, infer from `task_name`, or weaken
  staffing, finalization, or child-delivery checks.
- Never retain plaintext hook assignments; keep only bounded content-free
  projections and artifact hashes.
- Do not touch Claude, ZCode, OpenClaw, or Hermes configuration.
- Do not push, open a PR, alter trackers, or dispatch hosted workflows without
  separate authorization.
