---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-21
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
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
  - docs/roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md
  - docs/roadmap/issue-AR-263-restore-codex-desktop-parent-hook-delivery.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/roadmap/AR-119-2919802e-accepted-outcome-proof.md
  - docs/roadmap/AR-119-f4f3d45e-hiring-risk-evidence.md
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
branch: codex/ar119-three-host-live-evidence
evidence_commit: 1a8071caf9a594d5b1330f1acc6ef1b9c3c6884b
minimum_ledger_commit: 38a734cb4cd0fb2d11eeee025904e5632a0559c7
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
- PR #310 merged AR-261 to exact main `692a9257`; reviewed head `717be676` has
  the same tree. `[skip ci]` was used and GitHub shows zero branch or merge
  workflow runs.
- Claude/Codex/ZCode were freshly installed from that merge. Current bundles
  are `1aa8ed45...`, `990e83d4...`, and `47e7bb7e...`; status reports zero
  runtime drift.
- Claude pair `2919802e...` passes the exact-main accepted-outcome reporter.
  AR-260 tracker #307 closed automatically with every acceptance item met.
- Ordinary Claude session `f4f3d45e...` detected the missing SAP specialty and
  attempted hiring, but terminal status was `pending_approval`; no case or
  contractor survived atomic rollback. AR-261 owns the reproduced technical
  `diagnosis` -> `medical` false positive before any second draw.
- AR-261 is merged and installed. Focused hiring tests pass 88/88 and all 12
  proportional local gates pass in 1.3 minutes. Tracker #309 remains open until
  a real post-fix hire is proven; AR-259 tracker #305 is closed.
- Post-fix Claude session `9b7c38b0...` loaded the exact installed hooks but
  stopped before staffing because Claude OAuth was expired. Receipt
  `93f0adfd...` records `workforce_provider_unavailable`, one failed Haiku
  planner attempt, and no hiring codes. Roster 31 -> 31; no child launched.
- Exact-main dashboard install exposed AR-262: its 3-second inspection cache
  expired before the 15-second poll could display slow Claude results. The
  local 30-second stale-horizon candidate passes 189 affected Python, 134 UI,
  the 802-test production spine, and 12/12 local gates; rendered views match CLI.
- **Option A's three-host pin phase is complete.** OpenClaw/Hermes are deferred,
  not waived; Rule 9 stays five-host and never closes on three.
## completed-evidence

- **Newest Claude draw:** pair `2919802e...`, parent session `e183f92c...`, trace
  `0ce39143...`. Producer and verifier completed through actual
  `codex-subscription`; acceptance event `0c2dc63a...` was recorded for the
  existing TypeScript contractor. The final report is `canary_passed=true`.
- Claude exited 0 without timeout/truncation; the reporter projected distinct
  host-observed child IDs and had no unmet prerequisite. No retry followed.
- Exact facts and limits: `AR-119-2919802e-accepted-outcome-proof.md`. The
  isolated profile retained no artifact/attestation, so no matrix cell moved.
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
3. Pair `2919802e...` closes AR-260 on exact main. It proves reuse, not a new
   hire or promotion, and the isolated profile retains no Rule-4 artifact.
4. Genuine hiring remains unproven. Codex CLI parent is proven, but this
   Desktop task has no current hook snapshot or Store binding; `loaded: none`
   is invalid fallback evidence. AR-263 owns that lifecycle defect. Codex child
   proof remains upstream-blocked; ZCode needs plural cards.
5. The first ordinary Claude hiring smoke is consumed. It created an unstaffed
   generic child only; do not repeat it. The no-cost evidence is
   `AR-119-f4f3d45e-hiring-risk-evidence.md`.
6. The first post-fix work unit is also consumed, but did not reach staffing:
   session `9b7c38b0...` failed on expired Claude OAuth with zero model tokens
   and zero cost. Do not retry it. The owner must restore Claude login and
   explicitly authorize a genuinely different draw.
7. AR-262 is locally live-proven and committed as `1a8071ca` / `38a734cb`.
   Tracker #311 is linked; publication, exact-main reinstall, and the final
   rendered parity proof remain open.
8. No provider draw followed the Desktop diagnosis, and no matrix cell moved.

## next-bounded-work-package

Keep Option A frozen. Owner-authorized sequence:

1. Push the clean AR-262 branch and open its non-draft PR; run no Actions.
2. Verify a clean rollup, merge with `[skip ci]`, and reinstall the dashboard
   from the exact main merge.
3. Re-prove rendered CLI parity from that exact merge and close tracker #311.
4. Owner action: restore Claude login, then authorize one genuinely different,
   telemetry-preceded hiring draw. If it hires, smoke Codex and ZCode for reuse.
5. Keep AR-263 separate and draw-free; use the proven CLI parent path until
   Desktop dispatches current hooks. Then publish the Linux OpenClaw/Hermes
   handoff on main for the next box.

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
  AR-260 tracker #307 is closed. Hosted Actions stay forbidden.
