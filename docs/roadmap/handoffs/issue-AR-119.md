---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-13
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-257-separate-decision-conformance-fixture-launcher.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/SESSION_HANDOFF.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar119-vision-mitigation-handoff
evidence_commit: 211563c799e167bee03bfd0fa60e3f2ca6cc9195
minimum_ledger_commit: ee82c602f2dc2d5e9632fc91b6dc071b50dc7541
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
must be loaded first after any compaction or session restart.

## checkpoint

- The current source pair is Codex runtime `211563c7` and ledger `ee8db873`;
  Desktop documentation is `1a6e4887`/`ee82c602`, cross-file CLI history is
  `45b21cdc`/`01730614`, and preflight design is `ccb1802c`/`a7e8cf54`.
- AR-255 is still open. Its first five acceptance gates are checkpointed;
  exact-candidate Claude Installed/Live proof remains open.
- ADR-0159 now binds exact CLI 0.147 and separately pinned Desktop alpha to a
  sealed v3 attestation. Current Sol/TUI and all 65 observed Desktop calls
  omitted the marker and remain safely unstaffed.
- Matrix candidate `211563c7` has no proven top-level cell. Rule 1 source and
  simulation are repaired on all five adapters; Claude and Codex Rule 4
  Implementation/Simulation are proven. Every Installed/Live layer is unproven.
- Tracker creation for AR-255 through AR-257 and tracker synchronization for
  locally reopened historical issues remain pending explicit authorization.
  No missing tracker write is represented as complete.
- The expanded evaluator first failed for `211563c7` at 149/151, then passed
  151/151 after the AR-257 repair; exec depth-two is parked negative per AR-180.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix is
  the sole completion authority. Candidate `211563c7` preserves all 45 cells
  without converting implementation or simulation into host proof.
- AR-255 now uses complete-universe inference, exact ordered multi-card v6
  delivery, install/config/roster fences, fail-open diagnostics, and sealed
  one-use delivery proof. Store-only state and caller mappings are diagnostic.
- SafeClaude retains its in-lifetime collector. Codex candidate `211563c7`
  preserves the exact CLI 0.147 profiles and adds a separate Desktop
  `0.147.0-alpha.6.6` profile. Its atomic policy accepts one exact root and only
  13 observed depth-one/depth-two V2 child tuples, rejecting eight unobserved
  cross-products.
  Disabled guardians and exec depth-two/deeper remain unsupported.
- Desktop seals the canonical owner and both depth-two edges, exact adjacent
  direct event/output evidence, copied history, files, profile, currentness,
  independent offsets, and the 64 MiB aggregate external limit.
- Exact preflight inventory: PATH TUI/exec Codex `0.147.0`, native SHA-256
  `935A1911...2AD9D`; Desktop `26.803.10989.0` with runtime
  `0.147.0-alpha.6.6`, native SHA-256 `59295889...69B3`. The observed Sol/TUI
  call omitted `encrypted_function_args` and carried a `gAAAAA...` message.
- The authentic CLI cross-file census remains 11/11. The content-safe Desktop
  probe resolves 52/52 V2 chains (47 depth one, 5 depth two); maximum external
  ancestry is 32,650,955 bytes and maximum resolver time is 2.765 seconds.
- Desktop verification passed 288/288 focused provenance/hook tests, 289/289
  focused plus anchor, and the 673-test fast spine with 6 skips. Its green
  baseline killed 20/20 scoped mutations with zero survived/invalid and
  `source_unchanged=true`; independent verification reproduced the result and
  reported no finding at any severity.
- Candidate `45b21cdc` retains the historical 131/131 decision-conformance
  result. For `211563c7`, dashboard UI passed 134/134, routing passed every
  threshold, and Ruff lint/format passed.
- Claude's earlier Rule-4 artifacts and Codex's prior TUI/Desktop/exec negatives
  remain prior-candidate context. No Agency canary, live rewrite, real Claude
  invocation, or exact-candidate Installed/Live proof ran.

## exact-blocker

1. **AR-180 — Codex support.** Candidate `211563c7` proves exact CLI 0.147 and
   Desktop `0.147.0-alpha.6.6` Implementation/Simulation. Exec depth-two is
   parked: no same-version sample exists, so it needs a live spawn or a drop.
2. **AR-255 — exact host proof.** After those support gaps close, obtain explicit
   authorization before exact install or live proof, including one current
   Claude artifact. Passing fake-runner integration is simulation only.
3. **AR-252 — automatic contractor critical path.** Record host-backed producer
   outcomes plus a distinct inference-selected verifier verdict; prove three
   accepted outcomes after seven days trigger automatic promotion.
4. **AR-253 — staffing rate, latency, and parity.** Add the fixed staffing eval,
   separate the successful recruiter call from bounded repair attempts, restore
   the 15-second cold gate, and obtain exact-candidate evidence on all five
   supported hosts.
5. **AR-125 — value.** Run the matched Agency-on/off corpus only after candidate
   and provider validity hold. Malformed or timed-out arms are invalid, never
   upstream losses.
6. Rule 9 remains derived and cannot close until Rules 1-8 are proven under the
   same candidate on Claude, Codex, ZCode, Hermes, and OpenClaw. Unavailable
   hosts remain visibly unproven.

## same-task-continuity

After restart or compaction, load this file and `AR-119-founding-vision.md`
first. Then read AR-119, AR-255, AR-180, ADR-0118, ADR-0156, and ADR-0158.
Confirm branch, runtime `211563c7`, minimum ledger `ee82c602`, status, and worklog
parity. Do not reconstruct retired Job B, plan-row, work-unit, grant, or
consumed-receipt transport from historical sections.

## next-bounded-work-package

No cell is negative, and `967b0a2c` proves R7 at source and simulation on the
four hosts with adapter classes; only its zcode simulation stays open, since
that host has no adapter and the parity suite sweeps generic instead. Remaining
unblocked work is R2 and R3 (cards reaching the parent caller, singly and
severally) and R5 (the spawn-origin absence proof). The machine's master switch
is off, which silently empties adapter evidence gathered outside that suite.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_verify_docs_schema.py tests/test_decision_conformance.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

Run focused tests and the named fast Python production spine before each
checkpoint. A checkout-local evaluator is authoritative until an exact artifact
is refreshed under explicit install authorization.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its opaque
  channel.
- Inference alone chooses specialists and contractors. Deterministic code may
  recall, filter hard-ineligible candidates, validate, budget, and correlate.
- Only a host-written artifact with exact card hashes before first child speech
  proves Rule 4. Agency rows and model prose are diagnostics.
- A plaintext-looking Codex tool argument is not proof. The current authorization
  call must contain the explicit empty host marker; only exact ancestor causal
  calls may omit it under the sealed v3 profile.
- Same-process private reflection and same-account transcript plus Store
  forgery are threat-model exclusions; do not describe the lease as protection
  from code already executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
