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
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
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
branch: codex/ar119-claude-outcome-evidence
evidence_commit: 00c4dc7ea901102ff4eab68b7973153e17da46ce
minimum_ledger_commit: ae8fc7c05dc7b3952f4936fa6d5e63150e08a0e2
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
- PR #308 merged AR-260 to exact main `00c4dc7e`; exact tree
  `e3c8dd03ff30db3041b3ba343ecdda16955a1349`. `[skip ci]` was used and GitHub
  shows zero branch or merge workflow runs.
- Claude/Codex/ZCode were freshly installed from that merge. All three launcher
  manifests name runtime digest `75e998e4af26...`; status reported zero drift.
- Claude pair `2919802e...` passes the exact-main accepted-outcome reporter.
  AR-260 tracker #307 closed automatically with every acceptance item met.
- Ordinary Claude session `f4f3d45e...` detected the missing SAP specialty and
  attempted hiring, but terminal status was `pending_approval`; no case or
  contractor survived atomic rollback. AR-261 owns the reproduced technical
  `diagnosis` -> `medical` false positive before any second draw.
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
4. Genuine hiring remains unproven. Codex parent is solid and its child proof
   is upstream-blocked. ZCode needs
   plural cards. OpenClaw/Hermes wait for the Linux box.
5. The first ordinary Claude hiring smoke is consumed. It created an unstaffed
   generic child only; do not repeat it. The no-cost evidence is
   `AR-119-f4f3d45e-hiring-risk-evidence.md`.

## next-bounded-work-package

Keep Option A frozen. Owner-authorized sequence:

1. Commit this exact-main Claude proof and its ledger as a clean recovery pair.
2. Finish AR-261's provider-free technical-diagnosis classifier repair, focused
   review, tracker authorization, and clean PR merge. Its focused 88-test suite
   and all 12 proportional local gates are green.
3. Freshly install that exact main. Run telemetry before each bounded
   evaluation and never retry a failed draw.
   Smoke Codex once with its supported trust bypass and ZCode once through its
   bundled Node CLI; preserve upstream visibility limits exactly.
4. Prove one genuine hire plus later reuse without duplicate contractors.
5. Compare Store-backed CLI views with the authenticated rendered dashboard.
6. Publish the Linux OpenClaw/Hermes handoff on main for the next box.

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
