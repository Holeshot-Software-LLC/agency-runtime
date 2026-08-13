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
evidence_commit: 45b21cdcdbaac789bda58d31653179fc1a9f5c65
minimum_ledger_commit: d9d5e9cc68bd98ee20fda5b4b55f011ae4d2bce4
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
must be loaded first after any compaction or session restart.

## checkpoint

- The current source pair is Codex runtime `45b21cdc` and ledger `01730614`;
  reviewed documentation is `e051dcc0`/`d9d5e9cc`, and the preflight design
  remains `ccb1802c`/`a7e8cf54`.
- AR-255 is still open. Its first five acceptance gates are checkpointed;
  exact-candidate Claude Installed/Live proof remains open.
- The AR-180 read-only exact-host preflight is complete. ADR-0159 now binds the
  exact CLI 0.147 plaintext path to a v2 sealed in-file or cross-file transcript
  attestation; the current Sol/TUI spawn omitted the marker and remains safely
  unstaffed.
- Matrix candidate `45b21cdc` has no proven top-level cell. Rule 1 source and
  simulation are repaired on all five adapters; Claude and Codex Rule 4
  Implementation/Simulation are proven. Every Installed/Live layer is unproven.
- Tracker creation for AR-255 through AR-257 and tracker synchronization for
  locally reopened historical issues remain pending explicit authorization.
  No missing tracker write is represented as complete.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix is
  the sole completion authority. Candidate `45b21cdc` preserves all 45 cells
  without converting implementation or simulation into host proof.
- AR-255 now uses complete-universe inference, exact ordered multi-card v6
  delivery, install/config/roster fences, fail-open diagnostics, and sealed
  one-use delivery proof. Store-only state and caller mappings are diagnostic.
- SafeClaude retains its in-lifetime collector. Codex candidate `45b21cdc`
  binds exact 0.147 CLI in-file ancestry plus authentic one-record TUI ancestry
  across unique bounded canonical parent/root rollouts. It seals complete
  prefixes and every causal edge, enforces independent offsets and a 64 MiB
  aggregate external limit, and rolls final-attestation failure back safely.
- Exact preflight inventory: PATH TUI/exec Codex `0.147.0`, native SHA-256
  `935A1911...2AD9D`; Desktop `26.803.10989.0` with runtime
  `0.147.0-alpha.6.6`, native SHA-256 `59295889...69B3`. The observed Sol/TUI
  call omitted `encrypted_function_args` and carried a `gAAAAA...` message.
- The authentic cross-file census resolves 11/11 chains: depth-one sparse 1,
  depth-one inherited 7, depth-two sparse 1, and depth-two inherited 2. Maximum
  external ancestry is 48,678,898 bytes; maximum resolver time is 3.809 seconds.
- Parent verification passed 365 focused tests and the 673-test fast spine with
  6 skips. Its scoped baseline passed, killed 19/19 mutations, and reported
  zero survived/invalid with `source_unchanged=true`.
- The exact-current adversarial review found no finding at any severity; it
  independently passed 200 tests and killed the same 19/19 mutations. Dashboard
  134/134, routing, Ruff, format, and documentation/schema gates pass.
- The complete decision-conformance evaluator exited zero in 883.1 seconds:
  baseline passed in 169,548 ms, all 131/131 mutations were killed, zero
  survived or were invalid, and `source_unchanged=true`.
- Claude's three earlier Rule-4 artifacts and Codex's earlier TUI/Desktop/exec
  negatives remain prior-candidate context. A routine real Codex TUI child was
  observed in preflight; no Agency canary, real Claude invocation, or exact-
  candidate Installed/Live proof ran, so those layers remain unproven.

## exact-blocker

1. **AR-180 — Codex support.** Candidate `45b21cdc` proves exact CLI 0.147
   in-file and authentic one-record TUI cross-file Implementation/Simulation.
   Separately pin Desktop `0.147.0-alpha.6.6`. Exec depth-two/deeper is
   unobserved; obtain a read-only real-host sample before any separate pin.
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
Confirm branch, runtime `45b21cdc`, ledger `01730614`, status, and worklog
parity. Do not reconstruct retired Job B, plan-row, work-unit, grant, or
consumed-receipt transport from historical sections.

## next-bounded-work-package

Separately pin and adversarially review the observed Desktop-alpha schema and
ancestry. Then obtain a read-only exec depth-two sample, if the host emits one,
before separately pinning it or requesting install/trust/live authorization.
Continue AR-252, AR-253, AR-125, and derived Rule 9 afterward.

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
  calls may omit it under the pinned v2 schema.
- Same-process private reflection and same-account transcript plus Store
  forgery are threat-model exclusions; do not describe the lease as protection
  from code already executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
