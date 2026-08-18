---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-18
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
evidence_commit: 1bd7e37c6ea3be66488941392a956c3323b0472c
minimum_ledger_commit: ee82c602f2dc2d5e9632fc91b6dc071b50dc7541
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. This file and the founding vision load first after any compaction
or restart; during the authorized loop (through 2026-08-18 23:59) load the
vision-completion brief and the loop status doc immediately after.

## checkpoint

- **WORK ON the branch above IN `C:\Workspaces\Holeshot Software\agency-runtime-ar119`**
  (a linked worktree, synced with origin/main). Changes reach main only via
  PR on a verified-CLEAN rollup. Never commit/stash in the primary checkout
  (owner WIP: `cli/eval_commands.py` + three untracked eval JSONs); push the
  shared ref FROM the primary. PRs #290-#293 merged 2026-08-18.
- **Machine**: all three hosts pin runtime digest `cc478bc88258…` (merge
  `99a7b3ac`, PR #287, owner small-unit policy), store schema 47 == checkout
  == launcher. PRs #288–#293 are docs-only: no reinstall owed. The state
  authority is `~/.agency-runtime/overnight-runtime-state.json`.

## completed-evidence

- **Matrix candidate is `1bd7e37c`** (docs commit; package tree ==
  merge `99a7b3ac`). **THREE rules — R2, R3, R7 — are proven at all four
  layers on claude**, resting on two live events (a fresh two-turn
  real-profile `claude -p` session). **R1, R4, R5 and R6 Installed/Live
  were claimed on 2026-08-18 and RETRACTED the same day by adversarial
  review**; the retraction reasons are in
  `AR-119-99a7b3ac-live-evidence.md` and must not be quietly re-promoted.
  The real gain is an **existence proof**: the first
  `[AGENCY INFERENCE TEAM v6]` envelope ever seen on this machine,
  pre-speech in a harness-spawned child, verified to the byte — but
  delivery ran **1 in 14** children at this candidate and
  `native_child_delivery_verifications` is still empty.
  R8 needs an owner-gated capture decision.
- AR-252's joint-verdict shape is settled as a delegated ruling in its
  issue doc; the one-use capability seal is deliberately unwidened.

## traps (machine-specific; do not rediscover)

- `git status` can lie here: a stale `core.worktree` in the shared
  `.git/config` (left by a remote-control session) redirected every
  worktree's git view to the wrong directory on 2026-08-17; repaired with
  `git config --unset core.worktree`. If files phantom-appear, check that
  first and verify with `Test-Path`, not git.
- `python -m agency_runtime...` imports from CWD first: PYTHONPATH cannot
  override it. Always `cd` into the intended tree (checkout or launcher
  `site-packages`) and assert `agency_runtime.__file__` before trusting an
  eval. One spawn-authority run tonight silently measured the stale
  primary; it was caught and discarded.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge gates and
  canaries by their own report, never a piped code.
- Prepend `C:\agency-cli` to PATH or hosts read "native unverified". The
  packaged `agency.exe` is schema-pinned; install with
  `python -m agency_runtime.cli install --agent <host>` from a clean
  main-equal checkout. Sessions predating an install keep the old
  launcher: restart, never reinstall.
- Canaries need `--timeout 420`; the ar119 venv needed `ensurepip` for
  gate 3; the full gate suite takes ~14.5 min, over the tool cap — run it
  detached and read its own summary. Eight preflight/litellm tests are red
  on clean main outside every gate and `test_platform_wheel.py` fails
  collection: pre-existing noise.

## exact-blocker

1. **Card delivery to harness-spawned children is 1-in-14 at this
   candidate, and the misses are unexplained.** One child got a fully
   bound v6 envelope; thirteen did not, including three in the measuring
   session itself whose record zeros carry no `[AGENCY` marker and for
   which **no receipt exists** — two show `SubagentStart` firing and
   writing "supplies no card". Parent-stage provider failures explain
   much of it (13 routing failures in that session) and Rule 8 permits
   abstention, but nothing binds a receipt to a child launch, so the rate
   cannot be read. Bind one and this becomes a measurement. This, not the
   acceptance draw, is the live Rule 4 blocker.
2. **AR-252** — the joint-verdict shape is settled as a delegated ruling in
   the issue doc (verifier-authored semantic half, collector-assembled
   binding half, division named in the envelope; the one-use canary-only
   capability seal deliberately NOT widened). The pairing collector build
   is next; nothing yet collects a real envelope.
3. **AR-253** — recruiter `staff_without_safe_team` (decision "staff",
   ranked list, empty selection) and planner `provider_no_valid_response`
   sampled all night from this session's own turns and both canary series;
   intermittent under load, not an outage; file receipts, don't chase
   provider fixes. Parent staffing succeeded at 02:58Z and 03:50Z.
4. **codex/zcode/openclaw/hermes** — unchanged: codex needs attended TUI
   trust (bypass evidence never counts as attended); zcode has no CLI on
   this box; openclaw/hermes run the owner packet on the owner's boxes.

## next-bounded-work-package

**The section 7.1 question is ANSWERED.** On 2026-08-18 at 11:15Z a clean
draw delivered the pure 138-char unit to the child judge over the
complete 71-candidate universe with the owner policy live, and the judge
**abstained** — first-pass only; the repair returned no valid answer, so
it is unconfirmed. A repair-confirmed post-policy decline would settle
it; any staffing refutes it.

The sharpest open engineering lead is now different: **three
harness-spawned children in one session got no card and no receipt
explains why.** Bind a receipt to every child launch and the 1-in-14
delivery rate becomes a measurement instead of a mystery. Series
discipline if measuring again: probe, ≥3 serialized runs, failures kept,
30-min backoff after two consecutive provider-stage kills.

## same-task-continuity

After restart or compaction: this file, `AR-119-founding-vision.md`, the
vision-completion brief (§6 stopping conditions, §7 priorities), then
`AR-119-vision-loop-status.md` (the running ledger, cycle log, series
ledgers, morning decisions). The matrix + `AR-119-99a7b3ac-live-evidence.md`
carry the proof state. Do not reconstruct retired Job B, plan-row,
work-unit, grant or consumed-receipt transport; do not re-chase the REFUTED
list in the overnight brief.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
agency eval routing --json --no-details && agency eval spawn-authority --json
python -m agency_runtime.cli host-canary claude --timeout 420   # readiness
# execute: --execute --confirm "RUN LIVE claude CANARY" --timeout 420
~~~

Run focused tests, the fast spine, and the matrix-evidence list before each
checkpoint. Judge every gate by its own summary; a push's hook gates are
not the spine.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its
  opaque channel. Inference alone chooses specialists and contractors.
- Only a host-written artifact proves Rule 4; Agency rows correlate only.
- Never mark a matrix cell without its named authority at the exact
  candidate; provisional/branch evidence must say so.
- Keep the 15,000 ms cold control fixed; automatic promotion stays on the
  critical path; no Agency-superiority claim without a valid matched
  corpus (AR-125).
- Loop authorizations (through 2026-08-18 23:59): branch pushes, PRs,
  merges on verified-CLEAN rollups only, installs on the three present
  hosts from a clean main-equal tree, serialized canaries, §5 delegated
  decisions recorded as rulings. Forbidden at all times: §3 of the brief
  (no re-auth, no openclaw/hermes installs, no tracker writes, no tags or
  force-pushes, no pushes to main, no roster retirement approvals, no new
  capture surfaces, never change `observability.capture_content`).
