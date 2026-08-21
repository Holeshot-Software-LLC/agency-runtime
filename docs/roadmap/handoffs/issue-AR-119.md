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
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
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
branch: codex/ar119-hiring-failure-evidence
evidence_commit: de9ef543bcb8c11208f1f0ded3ebddf89157a438
minimum_ledger_commit: 13413c532abab9c66199ab8464455697165bc1e1
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
- PR #304 merged the recruiter repair to exact main `c279bca9`; exact tree
  `24fc346c471c248c3b464fd3a19b15b27976186e`. `[skip ci]` was used and no
  hosted run was observed.
- Claude/Codex/ZCode were freshly installed from that merge. Bundle digests
  start `ed5441f0dd04`, `3e546e6e37b1`, and `34d211f366eb`; dashboard reachable.
- This branch adds the local AR-259 terminal-hiring diagnostic. Focused tests
  pass 103/103; all 12 proportional local gates pass in 1.3 minutes at ledger
  head `13413c53`. AR-259 tracker #305 is open with `epic:observability`; the
  strict global tracker audit is red only on older recorded backlog items.
- **Option A's three-host pin phase is complete.** OpenClaw/Hermes are deferred,
  not waived; Rule 9 stays five-host and never closes on three.
## completed-evidence

- **Newest Claude draw:** pair `fcffd96c…`, run `905edae0…`, session
  `b6aed0c9…`, trace `6ded2097…`, failure `9864c8f6…`. Haiku planner applied;
  pinned `codex-subscription/gpt-5.6-terra` recruiter applied; staffing ended
  `no_safe_sufficient_team` / `recruiter_abstained` before child judging.
  Host exited 0; wrapper red at `delivery_marker_absent`; no outcome or promotion.
- The active `typescript-application-engineer` is an exact semantic match, so
  the draw was safe but poor selection. Empty hiring reasons cannot prove whether
  hiring was skipped or a deferred terminal event rolled back. AR-259 preserves
  closed status and inference consumption on the next receipt. No retry followed.
- Exact facts and limits: `AR-119-fcffd96c-hiring-diagnostic-evidence.md`.
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
3. Pair `fcffd96c…` then proved a valid applied recruiter abstention. Current
   receipts cannot distinguish no hiring event from a successful deferred event
   rolled back after later failure. AR-259 is the next deterministic blocker.
4. Codex parent is solid and its child proof is upstream-blocked. ZCode needs
   plural cards. OpenClaw/Hermes wait for the Linux box.

## next-bounded-work-package

Keep Option A frozen. Owner-authorized sequence:

1. Reuse clean local recovery pair `de9ef543` / `13413c53`; all 12 proportional
   gates and documentation validation are green.
2. Reuse the authorized AR-259 tracker
   [#305](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/305).
3. Publish a non-draft `[skip ci]` PR, verify CLEAN/no hosted run, merge, fetch
   exact main, and install Claude/Codex/ZCode from that merge.
4. Run one telemetry check before each bounded live evaluation; never retry a
   draw. The next Claude receipt must decisively name the hiring branch.
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
  AR-259 tracker #305 is created. Hosted Actions stay forbidden.
