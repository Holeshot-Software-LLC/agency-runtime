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
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
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
branch: codex/ar264-exact-main-smoke-evidence
evidence_commit: f76050d786cda3a4bc545d3d506d8c1687ce3574
minimum_ledger_commit: 1fd292b016f67429ca51289430974ffb2dd8382f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Load this file and the founding vision first, then the newest loop-status
sections. This is a recovery map, not evidence that an unproven matrix cell
moved.

## checkpoint

- Work only in `C:\Workspaces\Holeshot Software\agency-runtime-ar264-rollout`
  on `codex/ar264-exact-main-smoke-evidence`. It is based exactly on merged
  remote main `f76050d7`; the primary checkout has owner work and is untouched.
- PR #312 merged the slow-host dashboard parity repair. PRs #314 and #315 merged
  contractor execution-profile v2 plus both shipped package-v1 migrations. All
  used `[skip ci]`; no hosted workflow ran.
- Exact main is installed into Claude, Codex, ZCode, and the dashboard. The real
  Store advanced all 15 known packaged contractors to revision 1 / v2 while
  preserving lineage and TypeScript's two accepted outcomes.
- Authenticated dashboard workforce and host projections converge exactly with
  CLI: 31 contractors at digest `401e883532e9...`, five host rows at
  `003caceee19d...`, and master generation 56. The stopped post-reboot dashboard
  task was started without reinstalling or changing config.
- The new Codex draw stopped at parent `workforce_inference_failed` before any
  Agency decision or child. The ZCode draw started a generic host child but its
  Agency parent planner failed through expired `claude-subscription`; its
  artifacts have zero v6 card markers. Neither draw was retried.
- Claude remains logged out. A completely new Codex Desktop task
  `01a02587-...` again received no lifecycle snapshot or first-response header;
  the hook log and Store have no task-correlated evidence. Its first user turn
  was the continuation prompt rather than exact `agency status`, so the strict
  prompt control remains unrun. No skill load was attempted without activation.
- **Option A's three-host pin phase remains complete.** OpenClaw and Hermes are
  deferred to Linux, not waived. Rule 9 remains five-host.

## completed-evidence

- The child-judge decline is provider-conditional over the digest-verified
  71-agent universe. Claude declined the 138-character control 0/3; Codex
  staffed it. Do not remeasure except with a falsification target.
- Canary child pins stay Claude -> `codex-subscription`, Codex ->
  `codex-subscription`, and ZCode -> `zcode-recruiter` / GLM. The separate
  Claude accepted-outcome parent recruiter pin remains `codex-subscription`.
- Claude pair `2919802e...` remains the exact-main accepted-outcome proof:
  producer and verifier answered through `codex-subscription`, and the reporter
  accepted one existing TypeScript outcome. It is reuse, not hiring/promotion.
- Codex parent routing and exact Store-backed header remain CLI-proven. Native
  child card delivery is still blocked by the upstream opaque collaboration
  surface; no Store projection may substitute for host-authored proof.
- ZCode retains prior one-card GLM child evidence. The current draw additionally
  proves its CLI and generic Agent child work, but not Agency staffing or the
  required plural-card contract.
- Provider-free exact-main hook tests pass for Claude, Codex, and ZCode skill
  tools, and the real Store holds 19 historical skill rows. A fresh installed
  task remains the live evidence boundary.
- R1/R4/R5/R6 remain retracted. R8 still costs a candidate advance and
  R2/R3/R7 re-anchor. No rule was promoted and **no matrix cell moved**.

## exact-blocker

1. Restore Claude CLI login before any new Claude or ZCode Agency-parent draw.
2. AR-263's Desktop hook-dispatch failure recurred in fresh task `01a02587-...`:
   no header, current hook-log event, Store run, or resident binding exists.
   The intended exact-status first prompt was not sent, so do not describe that
   specific control as executed or publish `loaded: none` as evidence. Codex
   child visibility remains a separate upstream blocker.
3. ZCode's ordinary parent planner reached Claude before the GLM child judge.
   Do not widen Option A into general parent routing to bypass authentication.
4. Genuine post-AR-261 hiring, ZCode plural-card proof, and fresh skill capture
   remain unproven. Consumed SAP, Erlang, Codex, and ZCode work units stay
   consumed.
5. OpenClaw and Hermes wait for the owner's Linux box. Hosted Actions remain
   forbidden and issue #132 stays open.

## traps (machine-specific; do not rediscover)

- `agency` on PATH is schema 45. Run `python -m agency_runtime.cli` from this
  checkout. `C:\agency-cli` contains host CLIs, not the Agency CLI.
- Canaries require `--timeout 420` and immediately preceding telemetry. Never
  judge a gate through a pipe.
- ZCode's real CLI is
  `C:\Users\lucas\AppData\Local\Programs\ZCode\resources\glm\zcode.cjs`.
- Never infer the provider from the parent host. Preserve the recorded provider
  receipt, exact host artifact, and no-result boundary independently.

## next-bounded-work-package

1. Preserve the fresh Desktop failure under AR-263. If the exact prompt control
   is repeated, start another new task and send exact `agency status` first.
2. Load one skill without spawning a child only after a Store-backed header is
   active; task `01a02587-...` was correctly left without a skill attempt.
3. Owner restores Claude authentication. Then authorize one genuinely different
   bounded Claude hiring draw; never replay SAP or Erlang.
4. After the parent path is healthy, run one ZCode plural-card proof with the
   existing GLM child pin and unchanged ordinary routing.
5. Update AR-264 and this checkpoint, run proportional local gates, publish a
   verified-clean `[skip ci]` PR, and prepare the exact-main Linux handoff.

## same-task-continuity

After restart: this file, founding vision, then the end of loop status. The
matrix and linked evidence carry proof state. Never restore retired Job B or
re-chase the brief's refuted list.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/verify_docs.py
python -m pytest tests/test_host_hooks.py::test_successful_tool_use_injects_updated_first_pass_header \
  tests/test_host_hooks.py::test_agency_hook_claude_records_real_tool_evidence_from_stdin \
  -q -W error
python -m agency_runtime.cli dashboard service status --json
python -m agency_runtime.cli status --json
git diff --check
~~~

## constraints

- Push/PR/merge/install/live-smoke/dashboard/handoff authority is current.
  Hosted Actions stay forbidden.
- Do not change provider routing, Option A pins, matrix cells, candidate commit,
  or accepted evidence without new proof and owner scope.
- Do not mutate the real Store manually or delete its pre-AR-264 backup.
- Do not clean, stash, reset, install from, or commit in the primary checkout.
