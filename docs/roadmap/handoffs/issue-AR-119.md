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
evidence_commit: 6ba837fa70e844f99dab646c5ab48d03bbed2e7c
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
  (a linked worktree, synced with origin/main). Changes reach main only via
  PR on a verified-CLEAN rollup. Never commit/stash in the primary checkout
  (owner WIP: `cli/eval_commands.py` + three untracked eval JSONs), and never
  install from it -- that WIP sits inside the published package tree. Push
  from THIS worktree; the pre-push fixture bug that made worktree pushes fail
  is fixed. PRs #290-#296 merged.
- **Machine**: all three hosts pin ONE digest `f7b84c8a40fa` (merge
  `6ba837fa`, PR #296), schema 47 everywhere, installed 2026-08-19. State
  authority: `~/.agency-runtime/overnight-runtime-state.json`.
- **Owner ruling 2026-08-18: done = claude, codex, zcode, in that order.**
  Rule 9 is UNCHANGED — five-host parity is still the claim; never close R9
  on three hosts.

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
  pre-speech in a harness-spawned child, verified to the byte — which
  `agency evidence children` finds but cannot verify (blocker 1). R8
  needs an owner-gated capture decision, or the real-profile fail-open
  turns already on disk.
- AR-252's joint-verdict shape is settled as a delegated ruling; the
  one-use capability seal is deliberately unwidened (blocker 1).

## traps (machine-specific; do not rediscover)

- **git config corruption, FIXED 2026-08-19 (PR #296):** the pre-push
  gates ran `git init` with an inherited `GIT_DIR`, re-initializing the
  real repository as `bare = true` once per push and breaking `git status`
  machine-wide. If git ever claims "must be run in a work tree" or files
  phantom-appear, check `core.bare` and `core.worktree` first.
- `python -m agency_runtime...` imports from CWD first and PYTHONPATH
  cannot override it: `cd` into the intended tree and assert
  `agency_runtime.__file__` before trusting any eval. Better, run the
  launcher's own `_bootstrap.py` under `-I -S`.
- Appending `; echo EXIT=$?` makes the harness see exit 0; judge by the
  report, never a piped code.
- Prepend `C:\agency-cli` to PATH or hosts read "native unverified". The
  packaged `agency.exe` is schema-pinned; install with
  `python -m agency_runtime.cli install --agent <host>` from a clean
  main-equal checkout. Sessions predating an install keep the old
  launcher: restart, never reinstall.
- Canaries need `--timeout 420`; the full gate suite takes ~14 min, over
  the tool cap — run it detached and read its own summary. Eight
  preflight/litellm tests are red on clean main outside every gate, and
  `test_platform_wheel.py` fails collection: pre-existing noise.

## exact-blocker

1. **Rule 4 Live can only be proven inside a canary run — the whole
   blocker is the one-use capability seal.** `agency evidence children`
   finds the live v6 delivery and refuses it with
   `host_hook_output_origin_not_proven`: the verification input is the
   one-use capability only the canary's in-lifetime private-lease
   collector may consume (ADR-0158), so a read-only projection can never
   supply it and `native_child_delivery_verifications` stays empty.
   **The same seal blocks AR-252's collector — decide it once, for both.**
   Receipts are NOT the problem (that claim was retracted): use
   `agency evidence child-launches`, which resolves each launch by three
   complementary keys. One silent hole remains: a child launched with no
   open parent run records nothing; fixing it needs a new lane, hence a
   SCHEMA_VERSION bump — sequence deliberately.
2. **AR-252** — joint-verdict shape settled as a delegated ruling in the
   issue doc; the collector build waits on the same seal as blocker 1.
3. **AR-253** — recruiter `staff_without_safe_team` and planner
   `provider_no_valid_response` rove across stages, interleaved with clean
   draws on identical code: load-shaped, provider-side. Receipts filed in
   the issue; don't chase provider fixes.
4. **Hosts**: codex trust resets on every install (owner re-trusted
   2026-08-19); zcode has no CLI here; **openclaw/hermes have NO Rule 4
   route at all** — no artifact reader, no canary, in-process delivery
   only. See the packet before installing them.

## next-bounded-work-package

**The section 7.1 question is ANSWERED.** On 2026-08-18 at 11:15Z a clean
draw delivered the pure 138-char unit to the child judge over the
complete 71-candidate universe with the owner policy live, and the judge
**abstained** — first-pass only; the repair returned no valid answer, so
it is unconfirmed. A repair-confirmed post-policy decline would settle
it; any staffing refutes it.

The next decision is the **one-use verified-delivery capability seal**
(blocker 1): it gates Rule 4 Live and AR-252's collector at once, and no
amount of measurement moves either until it is settled. Series discipline
if measuring again: probe, ≥3 serialized runs, failures kept, 30-min
backoff after two consecutive provider-stage kills.

## same-task-continuity

After restart or compaction: this file, `AR-119-founding-vision.md`, the
vision-completion brief (§6, §7), then `AR-119-vision-loop-status.md` (the
ledger, series results, corrections, morning decisions). The matrix and
`AR-119-99a7b3ac-live-evidence.md` carry the proof state. Do not
reconstruct retired Job B, plan-row, work-unit, grant or consumed-receipt
transport; do not re-chase the overnight brief's REFUTED list.

## verification

~~~text
python scripts/run_local_gates.py          # full, ~14.5 min, run detached
python scripts/run_local_gates.py --fast   # skips the production spine
agency eval routing --json --no-details && agency eval spawn-authority --json
python -m agency_runtime.cli host-canary claude --timeout 420   # readiness
# execute: --execute --confirm "RUN LIVE claude CANARY" --timeout 420
~~~

Run focused tests, the fast spine, and the matrix-evidence list before each
checkpoint. Judge every gate by its own summary; a push's hooks are not
the spine. `agency evidence children --host claude --json` reads child
delivery without touching the store.

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
