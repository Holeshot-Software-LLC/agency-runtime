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
evidence_commit: e8b60f64b24968496f88a25d9935f4cfd77f3fe9
minimum_ledger_commit: 4026ddd67d491b5e85e80dc9bc939bdd2405510f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
must be loaded first after any compaction or session restart.

## checkpoint

- The current source pair is Codex runtime `e8b60f64` and ledger `4026ddd6`;
  the reviewed preflight design remains `ccb1802c`/`a7e8cf54`.
- AR-255 is still open. Its first five acceptance gates are checkpointed;
  exact-candidate Claude Installed/Live proof remains open.
- The AR-180 read-only exact-host preflight is complete. ADR-0159 binds the
  Codex 0.147 plaintext path to a sealed exact-call transcript attestation;
  the current Sol/TUI spawn omitted the marker and remains safely unstaffed.
- Matrix candidate `e8b60f64` has no proven top-level cell. Rule 1 source and
  simulation are repaired on all five adapters; Claude Rule 4 source and
  simulation are proven. Codex Rule 4 remains conservatively unproven because
  real host shapes remain unsupported. Every Installed/Live layer is unproven.
- Tracker creation for AR-255 through AR-257 and tracker synchronization for
  locally reopened historical issues remain pending explicit authorization.
  No missing tracker write is represented as complete.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix is
  the sole completion authority. Candidate `e8b60f64` preserves all 45 cells
  without converting implementation or simulation into host proof.
- AR-255 now uses complete-universe inference, exact ordered multi-card v6
  delivery, install/config/roster fences, fail-open diagnostics, and sealed
  one-use delivery proof. Store-only state and caller mappings are diagnostic.
- SafeClaude retains its in-lifetime collector. Codex candidate `e8b60f64`
  binds separate root/thread identities for exact 0.147 TUI and exec ancestry;
  final attestation failure rolls back the applied route so retry remains safe.
- Exact preflight inventory: PATH TUI/exec Codex `0.147.0`, native SHA-256
  `935A1911...2AD9D`; Desktop `26.803.10989.0` with runtime
  `0.147.0-alpha.6.6`, native SHA-256 `59295889...69B3`. The observed Sol/TUI
  call omitted `encrypted_function_args` and carried a `gAAAAA...` message.
- Candidate verification passed 342 focused tests, the 673-test fast spine with
  6 skips, 134 dashboard tests, every routing gate, Ruff, format, docs/schema,
  and whitespace checks. Telemetry reported 70.6 percent remaining.
- Decision conformance passed its baseline, killed 112/112 mutations with zero
  survived or invalid, and reported `source_unchanged=true`.
- The exact-current adversarial review found no unresolved finding at any
  severity; it independently passed 323 focused tests and killed 29/29 scoped
  mutations with zero survived or invalid.
- Claude's three earlier Rule-4 artifacts and Codex's earlier TUI/Desktop/exec
  negatives remain prior-candidate context. A routine real Codex TUI child was
  observed in preflight; no Agency canary, real Claude invocation, or exact-
  candidate Installed/Live proof ran, so those layers remain unproven.

## exact-blocker

1. **AR-180 — Codex support.** Candidate `e8b60f64` passes its source gates.
   Add trusted cross-file ancestry for authentic one-record TUI forks; separately
   pin Desktop `0.147.0-alpha.6.6`. Exec depth-two/deeper is unobserved and
   unsupported; obtain a read-only real-host sample before any separate pin.
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
Confirm branch, runtime `e8b60f64`, ledger `4026ddd6`, status, and worklog
parity. Do not reconstruct retired Job B, plan-row, work-unit, grant, or
consumed-receipt transport from historical sections.

## next-bounded-work-package

Implement and adversarially review trusted cross-file ancestry for authentic
one-record TUI fork prefixes. Then separately pin the observed Desktop-alpha and
obtain a read-only exec depth-two sample, if the host emits one, before separately
pinning it or requesting install/trust/live authorization. Continue AR-252,
AR-253, AR-125, and derived Rule 9 afterward.

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
- A plaintext-looking Codex tool argument is not proof. The explicit host marker
  must be bound to the exact persisted call before Agency rewrites it.
- Same-process private reflection and same-account transcript plus Store
  forgery are threat-model exclusions; do not describe the lease as protection
  from code already executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
