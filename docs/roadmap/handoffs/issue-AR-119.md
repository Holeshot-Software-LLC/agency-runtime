---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-20
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
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
branch: codex/ar119-windows-harness-live-evidence
evidence_commit: 95356cfa8b214d784e63c3d3da2ccd87e06fa5c5
minimum_ledger_commit: b2727ad8f950bab85f3ff5e5f990137f95fca9d0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status
sections. This is a recovery map, not evidence that an unproven cell moved.

## checkpoint

- **WORK ONLY in `C:\Workspaces\Holeshot Software\agency-runtime-main-rollout`**.
  The primary checkout has owner WIP; never commit, revert, stash, install, or
  clean there.
- PR #306 merged AR-259 to exact main `06f10171`; exact tree
  `5090b4ab3234d4d31e0764b1c7e11b580e6b4e76`. `[skip ci]` was used and no
  hosted run was observed.
- Claude/Codex/ZCode were freshly installed from that merge. All three launcher
  manifests name runtime digest `3951cb369726...`; status reported zero drift.
- This branch adds AR-260's reporter-only launch-binding repair. Focused tests
  pass 14/14, widened outcome/delivery tests pass 84/84, and all 12 local fast
  gates pass in 1.3 minutes at ledger head `b2727ad8`. Tracker #307 is open with
  `epic:observability`.
- **Option A's three-host pin phase is complete.** OpenClaw/Hermes are deferred,
  not waived; Rule 9 stays five-host and never closes on three.
## completed-evidence

- **Newest Claude draw:** pair `9685a16d…`, parent session `bf098816…`, trace
  `35175ce8…`. Producer and verifier children completed through requested
  `codex-subscription`; the Store recorded one accepted outcome for the existing
  TypeScript contractor. The host collector returned `accepted`.
- The wrapper rejected only the final projection because both supported Claude
  routes were bound by `launch_id` while the reporter required `child_id`.
  AR-260 admits only exact verified child-ID or launch-ID shapes. No retry ran.
- Exact facts and limits: `AR-119-9685a16d-accepted-outcome-evidence.md`.
  Disposable artifacts were cleaned, so Store correlation moves no matrix cell.
- **Codex parent works; child proof is blocked.** Parent routing/header pass.
  Its 0.148 draw failed parent preflight before spawn; the upstream opaque child
  surface remains a distinct limitation, not proof that Codex itself fails.
- **Claude reached verified delivery.** Decision `native-child-7624e16e…`
  delivered `minimal-change-engineer` pre-speech through `codex-subscription`.
- **ZCode:** exact parent header and one-card GLM child delivery are live-proven;
  plural-card Rule 4, accepted outcomes, promotion, and latency remain open.
- R1/R4/R5/R6 remain retracted. R8 costs candidate advance and re-anchoring.
  No rule was promoted and **no matrix cell moved** on 2026-08-20.
## traps (machine-specific; do not rediscover)

- **`agency` on PATH is `~/.local/bin/agency.exe` and is SCHEMA 45** -- it
  refuses the schema-47 store. Run `python -m agency_runtime.cli ...` from
  a main-equal checkout instead. `C:\agency-cli` holds the HOST CLIs
  (`claude.CMD`, `codex.CMD`), not the Agency CLI.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge the report.
  Install only clean main-equal code; restart stale sessions, never reinstall.
- Canaries need `--timeout 420`; run telemetry immediately before each one.
- ZCode installs no PATH command. Its real CLI is
  `C:\Users\lucas\AppData\Local\Programs\ZCode\resources\glm\zcode.cjs`.
  Version 0.16.3 advertises but rejects `--allowed-tools`, `--max-turns`, and
  `--settings`; native `ZCODE_MODEL`, `ZCODE_BASE_URL`, and `ZCODE_API_KEY`
  process overrides work while the permanent hook config remains unchanged.

## exact-blocker

1. The child judge decline is provider-conditional over the digest-verified
   71-agent universe: Codex staffs the 138-character control; Claude declined
   0/3. Option A stays frozen; do not remeasure without a falsification target.
2. Pair `39ff6dca…` proved the parent recruiter pin reached Codex but returned
   two unsafe teams. PR #304 repaired that output contract, not routing.
3. Pair `9685a16d…` reached an accepted host collection, but the old reporter
   rejected Claude's exact launch-ID binding. AR-260 is locally green and must
   be published, installed, and proven once without retry.
4. The draw reused a contractor; genuine hiring remains unproven. Codex parent
   is solid and its child proof is upstream-blocked. ZCode needs
   plural cards. OpenClaw/Hermes wait for the Linux box.

## next-bounded-work-package

Keep Option A frozen. Owner-authorized sequence:

1. Reuse clean local recovery pair `95356cfa` / `b2727ad8`; focused 14/14,
   widened 84/84, all 12 local gates, and documentation validation are green.
2. Reuse the authorized AR-260 tracker
   [#307](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/307).
3. Publish a non-draft `[skip ci]` PR, verify CLEAN/no hosted run, merge, fetch
   exact main, and install Claude/Codex/ZCode from that merge.
4. Run one telemetry check before the bounded Claude evaluation; never retry.
   The reporter must accept only the exact verified route/delivery projection.
5. Once Claude is solid, smoke Codex once with its supported trust bypass and
   ZCode once through its bundled Node CLI. Prove one genuine hire plus reuse,
   not duplicate contractors per host.
6. Compare Store-backed CLI views with the rendered authenticated dashboard.
7. Publish the Linux OpenClaw/Hermes handoff on main for the next box.

## same-task-continuity

After restart: this file, founding vision, then the end of the loop status.
The matrix and linked diagnostic/live evidence carry proof state. Never
restore retired Job B or re-chase the brief's REFUTED list.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
~~~

Judge each gate by its own summary; push hooks are not the production spine.

## constraints

- Codex remains supported; never weaken evidence to hide its opaque channel.
  Only host-written artifacts prove Rule 4; Agency rows correlate only.
- Never mark a matrix cell without its named authority at the exact
  candidate; provisional/branch evidence must say so.
- Keep the 15,000 ms cold control fixed; automatic promotion stays on the
  critical path; no superiority claim without a matched corpus (AR-125).
- Push/PR/merge/install/live-smoke/dashboard/handoff authority is current.
  AR-260 tracker #307 is created. Hosted Actions stay forbidden.
