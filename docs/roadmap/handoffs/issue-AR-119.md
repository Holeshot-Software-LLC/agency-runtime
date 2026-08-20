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
branch: codex/ar119-claude-outcome-live-evidence
evidence_commit: aa6439b1c84c4ef4c7b95d17c530a586bf4c08b4
minimum_ledger_commit: f1f196bc983a1e55d8e5fb108117509a736a6c71
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for the owner-confirmed nine-rule vision. Load this
file and the founding vision first, then the loop status for current state.

## checkpoint

- **WORK ON the branch above IN `C:\Workspaces\Holeshot Software\agency-runtime-main-rollout`**.
  It starts at exact main `a102a932` / PR #302; the primary checkout's
  named owner WIP remains untouched; never commit, revert, stash, or install there.
  Hosted CI was skipped at PR head and merge; local gates govern.
- **Machine**: Claude is at `a102a932` (`4c6d8a17…` / `b0b5073c…`); Codex
  retains PR #298 and ZCode `f203dc66`. Readiness is green; the map remains
  `claude/codex -> codex-subscription`, `zcode -> zcode-recruiter`; ordinary
  providers remain Codex then Claude and content capture remains enabled.
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
- **PR #302 merged the preflight repair** at `a102a932`; its draw reached recruiter safety. The local parent pin passed 797/20 + 12/12, not config/live.
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
   Exact-main pair `6e0eff11…` proved the 2,367-char repair: Haiku planner
   applied. Sonnet recruiter then failed `staff_without_safe_team` and its
   repair had no valid response; no route, child judge, outcome or promotion.
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
5. **Merged-main ZCode parent blocker is closed.** PR #299 is merged, ZCode is
   reinstalled from `f203dc66`, deterministic smoke is 4/4, and CLI session
   `sess_d4ac6d99…` was accepted on the first real provider request. The host
   answered through Z.ai/GLM-5.3 while Agency correctly reported its separate
   Claude/Sonnet workforce receipt. Extra `Why`/`How` prose is follow-up debt.

## next-bounded-work-package

Keep Option A frozen. The full sequence requested at the 19 August review is:

1. Claude: the local canary-only `claude -> codex-subscription` parent-recruiter
   pin is implemented; owner config remains unset. Finish gates/recovery, then
   seek fresh publication, config, exact-main install, and one-draw authority.
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
The matrix and `AR-119-99a7b3ac-live-evidence.md` carry proof state. Never
restore retired Job B or re-chase the brief's REFUTED list.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
python -m agency_runtime.cli eval routing --json --no-details
~~~

Judge each gate by its own summary; push hooks are not the production spine.

## constraints

- Codex remains supported; never weaken evidence to hide its opaque channel.
  Only host-written artifacts prove Rule 4; Agency rows correlate only.
- Never mark a matrix cell without its named authority at the exact
  candidate; provisional/branch evidence must say so.
- Keep the 15,000 ms cold control fixed; automatic promotion stays on the
  critical path; no superiority claim without a matched corpus (AR-125).
- PR #302 push/merge, Claude exact-main install, and its one live draw are
  consumed. Fresh authority is required for any push/PR/merge/install/provider
  draw or config change; OpenClaw/Hermes remain exempt, not waived.
