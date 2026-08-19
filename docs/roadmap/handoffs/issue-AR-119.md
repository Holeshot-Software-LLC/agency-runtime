---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-19
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-completion-autonomous-brief.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-99a7b3ac-live-evidence.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-vision-mitigation-handoff
evidence_commit: 14de2f74659eb87721daf433c927691a69c27aed
minimum_ledger_commit: ee82c602f2dc2d5e9632fc91b6dc071b50dc7541
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. This file and the founding vision load first after any compaction
or restart, then `AR-119-vision-loop-status.md` for current state.

## checkpoint

- **WORK ON the branch above IN `C:\Workspaces\Holeshot Software\agency-runtime-ar119`**
  (linked worktree). Main only via PR on a verified-CLEAN rollup. Never
  commit/stash/install in the primary checkout; owner WIP remains there.
  **PR #298 is at `758fd944`; `74c31def` plus this recovery pair are local.
  Owner-authorized: push/merge, merged-main install, Claude/ZCode smokes, and one
  Codex hook-trust-bypass canary. Hosted CI must be skipped; local gates govern.**
- **Machine**: Claude/Codex remain on installed launcher `51b3202a2acb`; ZCode
  now runs verified repair `f24664b87f3b`. The canary map remains
  `claude/codex -> codex-subscription`, `zcode -> zcode-recruiter`; ordinary
  providers remain Codex then Claude and content capture remains enabled.
- **Option A's local three-host provider-pin phase is complete.** OpenClaw and
  Hermes are deferred, not waived. Rule 9 stays five-host and never closes on three.
## completed-evidence

Detail in `AR-119-vision-loop-status.md`, session 2026-08-19. **No matrix
cell moved.** Candidate is still `1bd7e37c`; R2, R3, R7 remain the only
four-layer rules on claude; R1, R4, R5, R6 stay RETRACTED
(`AR-119-99a7b3ac-live-evidence.md`) -- no quiet re-promotion.

- **R8 claude is provable from disk, no new capture surface.** Run
  `e9715480` / trace `2a77824c` (session `abaccac6`, real profile,
  `preflight_failed`) retains the entire delivered context INLINE in the
  host transcript: 1,309 chars, steward kernel only, no `[AGENCY LOADED]`.
  The unstaffed negative is OBSERVED, not borrowed like R5's. Store: 0
  specialists/routing/delegations on the trace. Claiming costs a
  `candidate_commit` advance to `f7b84c8a40fa` + re-anchoring R2/R3/R7.
- **Codex parent works; child proof is blocked.** A current request-scoped
  parent turn has preflight inference, a loaded capsule and the Agency header.
  Three byte-identical canaries still show Codex spawns and starts the child,
  but Agency cannot READ the collaboration.
  `native_collaboration_topology_invalid` is the diagnostic's terminal
  fall-through reached with every guard PASSING -- not an invalid topology.
  Do not rerun its byte-identical child canary.
- **Claude reached verified delivery.** Attempt 1 stopped at parent preflight.
  Attempt 2 produced one pre-speech host artifact and the Store's first
  `native_child_delivery_verifications` row: decision `native-child-7624e16e…`,
  `minimal-change-engineer`, requested/answered `codex-subscription`, confidence
  0.91, candidate `59580436f7f1`. The overall report stayed red only because it
  compared that child team with the parent's `code-reviewer` team. `14de2f74`
  fixes the correlation and provider projection; 134 affected tests pass.
  After reinstall, two bounded refreshes stopped at parent preflight: oversized
  teams (`3832e7aa…`), then no valid planner (`c7ae4580…`). Neither called a child.
## traps (machine-specific; do not rediscover)

- **`agency` on PATH is `~/.local/bin/agency.exe` and is SCHEMA 45** -- it
  refuses the schema-47 store. Run `python -m agency_runtime.cli ...` from
  a main-equal checkout instead. `C:\agency-cli` holds the HOST CLIs
  (`claude.CMD`, `codex.CMD`), not the Agency CLI.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge by the
  report. Installs need a clean main-equal checkout; sessions predating an
  install keep the old launcher -- restart, never reinstall.
- Canaries need `--timeout 420`; the gate suite ~14 min, run detached.
  Eight preflight/litellm tests red on clean main and
  `test_platform_wheel.py` collection failure are pre-existing noise.

## exact-blocker

1. **CONFIRMED 2026-08-19: the child judge's decline is
   provider-conditional.** `agency.yaml` lists `codex-subscription` first
   with `judge.model` empty; the canary's restricted profile has no codex
   transport and falls through to `claude-subscription`. Over a
   digest-verified identical 71-agent universe with the byte-identical
   138-char unit: `codex-subscription` **STAFFS** (`minimal-change-engineer`,
   0.90/0.93) and `claude-subscription` **DECLINES** (0 staffed / 3, two
   applied+inferred declines at confidence **0.75 -- the same confidence the
   canary's own child decision `5c963e09` recorded**). Reproduce with
   `python scripts/ar119_child_judge_probe.py --provider <name> --runs 3`.
   **This retracted this session's own "7.1 settled" claim** and killed the
   reading that the decline is a small-unit-policy property. Two
   environments disagree about whether the same child needs a specialist --
   an owner question, and AR-253's rather than AR-119's.
2. **The one-use capability seal** still gates Rule 4 Live and AR-252. Two
   gates in `child_delivery_evidence.py`: the `expected` capability
   (read-only paths hardcode `structural_hook_output=False`, lines
   1151/1226) and the sealed atomic Store consumer.
   `native_child_delivery_verifications` now has **1 verified Claude row** from
   the pre-fix report above; it has not moved a matrix cell. Gate 1 exists
   because Claude Code tags no substring as hook-authored (1147-1150).
   **Neither option moves codex**: `_expected_v6_reason` returns
   `unsupported_opaque_interagent_channel` on its FIRST line.
3. **Option A is locally complete for the owner-scoped three-host pin phase.**
   Claude has an exact requested/answered `codex-subscription` route. Codex
   parent works and its child-proof exception remains explicit. Repaired ZCode
   route `native-child-aa6e5296…` requested/answered `zcode-recruiter`/GLM,
   selected `python-application-engineer`, and bound v6 card to `call_1f2255f…`.
   Host child `agent_07b6377b…` carries the byte-exact card in record zero;
   14/14 mechanical checks pass. No Rule was re-promoted and no cell moved.
4. **Hosts**: Codex parent routing/header delivery is operational. Its Rule-4
   child artifact remains upstream-blocked; never summarize that as “Codex
   does not work.” Codex is trusted + on claude's digest
   (`hook_trust_status: unverified` = a missing `--verify-activation`
   receipt, NOT the owner's trust action). ZCode 3.8.1 is live-proven for this
   one-card bounded call; openclaw/hermes have no Rule 4 route.

## next-bounded-work-package

Keep Option A frozen. The owner-requested Codex rerun after the exact main
install is one new bounded observation, not a variation campaign; do not retry
Claude or ZCode. Then resume the 2–4 day primary-tool seal/AR-252 package plus
Lucas's separate Rule-8 candidate choice. OpenClaw/Hermes remain deferred.

## same-task-continuity

After restart or compaction: this file, `AR-119-founding-vision.md`, the
brief (§6, §7), then `AR-119-vision-loop-status.md` (ledger, series results,
corrections). The matrix and `AR-119-99a7b3ac-live-evidence.md` carry proof
state. Do not reconstruct retired Job B, plan-row, work-unit, grant or
consumed-receipt transport; do not re-chase the brief's REFUTED list.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
python -m agency_runtime.cli eval routing --json --no-details
python -m agency_runtime.cli host-canary claude --timeout 420   # readiness
# execute: --execute --confirm "RUN LIVE claude CANARY" --timeout 420
~~~

Judge every gate by its own summary; a push's hooks are not the spine.
`agency evidence children --host claude --json` and `evidence rejections`
read without touching the store.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its
  opaque channel. Inference alone chooses specialists and contractors, and
  only a host-written artifact proves Rule 4; Agency rows correlate only.
- Never mark a matrix cell without its named authority at the exact
  candidate; provisional/branch evidence must say so.
- Keep the 15,000 ms cold control fixed; automatic promotion stays on the
  critical path; no superiority claim without a matched corpus (AR-125).
- Owner authorization dated 2026-08-19 covers PR #298 update/merge, merged-main
  install, Claude/ZCode parent smokes, and one Codex child canary with
  `--dangerously-bypass-hook-trust`. It excludes hosted CI, OpenClaw/Hermes,
  trackers, tags, force/direct main pushes, new capture, re-auth, or config changes.
