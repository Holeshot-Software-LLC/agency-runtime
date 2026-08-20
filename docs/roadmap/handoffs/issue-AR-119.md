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
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-vision-completion-autonomous-brief.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
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
branch: codex/ar119-recruiter-safe-team-contract
evidence_commit: e7e4e2858f761fb898fce4b17a147c3655b0ec17
minimum_ledger_commit: 1dd70983e0bd14a9e59fcba83918db53f8772b6b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for the owner-confirmed nine-rule vision. Load this
file and the founding vision first, then the loop status for current state.

## checkpoint

- **WORK ON the branch above IN `C:\Workspaces\Holeshot Software\agency-runtime-main-rollout`**.
  It starts at exact main `eff66c67` / PR #303; the primary checkout's
  named owner WIP remains untouched; never commit, revert, stash, or install there.
  Hosted CI was skipped at PR head and merge; local gates govern.
- **Machine**: all three projections were refreshed from `eff66c67`; Claude
  bundle is `6e8353a3…`, Codex `ccfe2351…`, ZCode `5ae16c9e…`. Child pins are
  Claude/Codex -> `codex-subscription`, ZCode -> `zcode-recruiter`; the distinct
  accepted-outcome Claude parent-recruiter pin is `codex-subscription`.
- **Option A's three-host pin phase is complete.** OpenClaw/Hermes are deferred,
  not waived; Rule 9 stays five-host and never closes on three.
## completed-evidence

Detail in `AR-119-vision-loop-status.md`, session 2026-08-19. **No matrix
cell moved.** Candidate is still `1bd7e37c`; R2, R3, R7 remain the only
four-layer rules on claude; R1, R4, R5, R6 stay RETRACTED
(`AR-119-99a7b3ac-live-evidence.md`) -- no quiet re-promotion.

- **R8 claude is provable from disk, no new capture surface.** Run `e9715480` /
  trace `2a77824c` retains the 1,309-char steward-only delivered context and
  zero Store staffing rows. Claiming it still costs candidate advance
  `f7b84c8a40fa` plus re-anchoring R2/R3/R7 -- an owner decision.
- **Codex parent works; child proof is blocked.** Parent routing/header pass.
  The one authorized 0.148 falsification draw used the trust bypass and requested
  `codex-subscription`, but parent preflight failed before spawn:
  `workforce_inference_failed`, spawn/start 0/0, `codex_parent_spawn_missing`.
  No child judge answered, so this neither proves nor falsifies the upstream
  plaintext surface and is not Rule-4 proof.
- **Claude reached verified delivery.** Decision `native-child-7624e16e…`
  delivered `minimal-change-engineer` pre-speech through answered
  `codex-subscription`; `14de2f74` repairs report correlation. Two later bounded
  refreshes stopped at parent preflight and never called a child.
- **ZCode parent header is exact-main live-proven.** PR #299 fixed the missing
  initial snapshot. Bundled CLI session `sess_d4ac6d99…` reached Z.ai once;
  requested `glm-5.2`, actual response model `glm-5.3`, zero tools. Agency trace
  `498d64b3…` finalized `accept/completed` with the exact five fields and no
  delegation. This is parent proof, not a Rule-4 cell.
- **PR #303 merged and installed the parent pin** at `eff66c67`; its one draw
  reached the requested provider but failed the recruiter's safe-team contract.
## traps (machine-specific; do not rediscover)

- **`agency` on PATH is `~/.local/bin/agency.exe` and is SCHEMA 45** -- it
  refuses the schema-47 store. Run `python -m agency_runtime.cli ...` from
  a main-equal checkout instead. `C:\agency-cli` holds the HOST CLIs
  (`claude.CMD`, `codex.CMD`), not the Agency CLI.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge the report.
  Install only clean main-equal code; restart stale sessions, never reinstall.
- Canaries need `--timeout 420`; the ~14-min gate suite runs detached. Eight
  preflight/litellm reds and the platform-wheel collection red pre-exist.
- ZCode installs no PATH command. Its real CLI is
  `C:\Users\lucas\AppData\Local\Programs\ZCode\resources\glm\zcode.cjs`.
  Version 0.16.3 advertises but rejects `--allowed-tools`, `--max-turns`, and
  `--settings`; native `ZCODE_MODEL`, `ZCODE_BASE_URL`, and `ZCODE_API_KEY`
  process overrides work while the permanent hook config remains unchanged.

## exact-blocker

1. **CONFIRMED 2026-08-19: the child judge's decline is provider-conditional.**
   Over the digest-verified identical 71-agent universe and byte-identical
   138-char unit, `codex-subscription` staffs `minimal-change-engineer`
   (0.90/0.93), while `claude-subscription` declines 0/3 (two at 0.75, matching
   decision `5c963e09`). Reproduce with `python
   scripts/ar119_child_judge_probe.py --provider <name> --runs 3`. This retracts
   "7.1 settled"; policy interpretation belongs to AR-253.
2. **The exactly-two capability decision is locally implemented.** The owner
   authorized two consumptions only inside one atomic producer/verifier pairing.
   Pair-scoped capabilities cannot enter the ordinary one-use consumer; exactly
   two Store-verified Claude artifacts, one producer output, and one verifier-
   artifact semantic line are required before the Store call.
   `native_child_delivery_verifications` now has **1 verified Claude row** from
   the pre-fix report above; it has not moved a matrix cell. Gate 1 exists
   because Claude Code tags no substring as hook-authored (1147-1150).
   **Neither option moves codex**: `_expected_v6_reason` returns
   `unsupported_opaque_interagent_channel` on its FIRST line.
   Exact-main pair `39ff6dca…` reached the pinned Codex recruiter twice but both
   outputs failed `staff_without_safe_team`; no child judge or outcome followed.
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
5. **The current package fixes the recruiter contract, not routing.** The two
   raw JSON bodies were not persisted; their exact retained projections and
   prompt limits are in `AR-119-39ff6dca-recruiter-diagnostic-evidence.md`.
   The local candidate defines mandatory/optional/excluded classifications,
   sends bounded safe-team repair facts, and retains only three diagnostic
   counts. Provider-free: 97 + 797/20 + 695; all 14 gates pass in 13.9 minutes.

## next-bounded-work-package

Keep Option A frozen. The full sequence requested at the 19 August review is:

1. Seek fresh authority for push/PR/merge, then exact-main install, config, and
   one bounded draw. Do none of those from this local checkpoint implicitly.
2. Codex: retain parent proof. The 0.148 draw stopped before spawn; do not
   repeat until a new upstream surface or deterministic preflight fix exists.
3. ZCode: retain this parent proof and existing one-card child proof, then close
   plural-card Rule 4, outcomes, promotion and latency on an exact merged install.
4. Move to the owner's OpenClaw box for route implementation and live proof;
   Hermes follows later. Both remain part of five-host completion.
5. Finish matched Agency-on/off and upstream corpora, cold/warm/fan-out bounds,
   matrix reconciliation and Rule 9; run hosted/release gates once at the end.

## same-task-continuity

After restart: this file, founding vision, then the end of the loop status.
The matrix and linked diagnostic/live evidence carry proof state. Never
restore retired Job B or re-chase the brief's REFUTED list.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
# Do not run provider-backed eval or host CLIs without fresh authority.
~~~

Judge each gate by its own summary; push hooks are not the production spine.

## constraints

- Codex remains supported; never weaken evidence to hide its opaque channel.
  Only host-written artifacts prove Rule 4; Agency rows correlate only.
- Never mark a matrix cell without its named authority at the exact
  candidate; provisional/branch evidence must say so.
- Keep the 15,000 ms cold control fixed; automatic promotion stays on the
  critical path; no superiority claim without a matched corpus (AR-125).
- PR #303 push/merge, exact-main install, config change, and its one live draw
  are consumed. Fresh authority is required for any push/PR/merge/install/provider
  draw or config change; OpenClaw/Hermes remain exempt, not waived.
