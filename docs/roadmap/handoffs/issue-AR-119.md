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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-vision-mitigation-handoff
evidence_commit: 4f34c1135c43e5601e79a94714e31f8107c61dda
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
  (linked worktree, synced with origin/main). Main only via PR on a
  verified-CLEAN rollup. Never commit/stash in the primary checkout (owner
  WIP: `cli/eval_commands.py` + three untracked eval JSONs) and never
  install from it -- that WIP sits in the published package tree. Push from
  THIS worktree. PRs #290-#297 merged. **The branch is PUSHED through
  `abc88dd9` (15 ahead of main, docs-only, 12/12 gates green). No PR yet.**
- **Machine**: all three hosts pin ONE digest `f7b84c8a40fa` (merge
  `6ba837fa`), schema 47 everywhere, installed 2026-08-19. State authority:
  `~/.agency-runtime/overnight-runtime-state.json`.
- **Owner ruling 2026-08-18: done = claude, codex, zcode, in that order.**
  Rule 9 UNCHANGED -- five-host parity is still the claim; never close R9
  on three hosts.
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
- **Codex canary: 3 serialized runs, byte-identical -- NOT the AR-253
  flake.** Planner and recruiter both `structured_response_applied`, yet
  preflight failed `workforce_inference_failed`. Codex spawns the child and
  it starts; Agency cannot READ the collaboration.
  `native_collaboration_topology_invalid` is the diagnostic's terminal
  fall-through reached with every guard PASSING -- not an invalid topology.
  The claude canary instead stops at `delivery_marker_absent`; codex never
  reaches the child judge.
## traps (machine-specific; do not rediscover)

- **git config corruption, FIXED 2026-08-19 (PR #296).** If git ever says
  "must be run in a work tree" or files phantom-appear, check `core.bare`
  and `core.worktree` first. Verified false/unset 2026-08-19.
- **`agency` on PATH is `~/.local/bin/agency.exe` and is SCHEMA 45** -- it
  refuses the schema-47 store. Run `python -m agency_runtime.cli ...` from
  a main-equal checkout instead. `C:\agency-cli` holds the HOST CLIs
  (`claude.CMD`, `codex.CMD`), not the Agency CLI.
- `python -m agency_runtime...` imports from CWD first and PYTHONPATH
  cannot override it: `cd` into the intended tree and assert
  `agency_runtime.__file__`. Better, run the launcher's `_bootstrap.py`
  under `-I -S`.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge by the
  report. Installs need a clean main-equal checkout; sessions predating an
  install keep the old launcher -- restart, never reinstall.
- Canaries need `--timeout 420`; the gate suite ~14 min, run detached.
  Eight preflight/litellm tests red on clean main and
  `test_platform_wheel.py` collection failure are pre-existing noise.

## exact-blocker

1. **The child judge's provider is picked by config list order, and it
   changes the answer.** Newest, probably largest. `agency.yaml` lists
   `codex-subscription` first with `judge.model` empty; the canary's
   restricted profile has no codex transport and falls through to
   `claude-subscription`. Measured over a digest-verified identical
   71-agent universe: the byte-identical 138-char canary unit **ABSTAINED**
   on `claude-subscription` (twice, one repair-confirmed) and **STAFFED** on
   `codex-subscription` (`minimal-change-engineer`, 0.90). **This retracted
   this session's own "7.1 settled" claim** -- any staffing refutes it --
   and killed the reading that the decline is a small-unit-policy property.
2. **The one-use capability seal** still gates Rule 4 Live and AR-252. Two
   gates in `child_delivery_evidence.py`: the `expected` capability
   (read-only paths hardcode `structural_hook_output=False`, lines
   1151/1226) and the sealed atomic Store consumer.
   `native_child_delivery_verifications` = **0 rows ever**. Gate 1 exists
   because Claude Code tags no substring as hook-authored (lines 1147-1150).
   **Neither option moves codex**: `_expected_v6_reason` returns
   `unsupported_opaque_interagent_channel` on its FIRST line.
3. **Option A is separable and cheap to wire.** Codex recognizer call sites
   are all gated on `host == "codex"`; the only non-host-aware consumer is
   `canary_proof.py:416`. Keeping `CANARY_PROMPT` aliased and adding a
   separate constant breaks NO existing test (baseline 21 passed). If
   blocker 1 is the cause, no new unit is needed at all.
4. **Hosts**: codex trusted + on claude's digest for the first time
   (`hook_trust_status: unverified` = a missing `--verify-activation`
   receipt, NOT the owner's trust action). zcode has no CLI; openclaw and
   hermes have no Rule 4 route. AR-253 flake still roving.

## next-bounded-work-package
**One measurement decides the seal.** Force the child-judge probe onto
`claude-subscription`; re-run the 138-char control over the same
digest-verified 71-agent universe.
- **Declines** -> provider-conditional, confirmed. Option A collapses to
  pinning the canary's judge provider: no new unit, no fixture change, no
  Rule 9 divergence. Decide the seal for Option A.
- **Staffs** -> the cause is the canary's isolated environment; examine the
  canary profile and prompt next.

The probe is read-only (calls `query_judge` exactly as `staff_native_child`
does; never `_unstaffed` / `_record_decision`). Rebuild its universe from
decision `5c963e09`'s `offered_agent_ids`, **validated against
`offered_agent_digest`** -- a naive re-filter with `capability_status=""`
yields 33, not 71, and silently measures a different universe.

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
- **Loop authorizations LAPSED 2026-08-18 23:59 -- re-ask before pushing,
  PRing, merging or installing.** Forbidden at all times (§3 of the brief):
  no re-auth, no openclaw/hermes installs, no tracker writes, no tags or
  force-pushes, no pushes to main, no roster retirement approvals, no new
  capture surfaces, never change `observability.capture_content`.