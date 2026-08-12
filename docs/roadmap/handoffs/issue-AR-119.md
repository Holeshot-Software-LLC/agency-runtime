---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-12
tags: [handoff, vision, inference, child-delivery, contractors, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
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
evidence_commit: e392c040c967a65822b0615101d581c7b978983f
minimum_ledger_commit: 6f4e6b64448d62f6c2aeadd7ecef236e71f9b8f1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded next-session mitigation plan for the nine-rule vision. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) retains history;
this is the single current bootstrap projection.

## checkpoint

- PR #270 merged to `main` as `e392c040` on 2026-08-12. Its PR gates were
  green. The post-merge push failed only because the merge commit was missing
  from the worklog; local ledger-only commit `6f4e6b64` repairs that row.
- This branch records the owner decisions: Codex remains supported; specialist
  and contractor choice is inference-only; only host-written artifacts prove
  child card delivery; latency must improve without weakening those controls;
  canonical drift must be reconciled; automatic contractor promotion is P0 and
  blocks AR-119.
- AR-255 and AR-256 are the new P0 repair records. AR-252 and AR-253 are
  restated for the current host-spawned/JIT architecture and elevated to P0.
  Tracker creation for all four remains pending explicit authorization.
- The complete owner-confirmed nine rules are now repository-local in
  `docs/roadmap/AR-119-founding-vision.md`; do not reconstruct them from issue
  fragments or external session memory.

## completed-evidence

- The canonical matrix has no current `proven` top-level cell. Its current
  source negatives are Rule 1 on Claude/Codex/ZCode, Rule 4 on Codex, and Rule
  8 on Hermes/OpenClaw; every host also has unproven exact-candidate installed
  and live layers. This is an evidence state, not a completion percentage.
- Claude has three prior-candidate Rule-4 host artifacts containing multiple
  exact cards before first speech. None binds the matrix's exact candidate, so
  current installed/live state is unproven; Agency Store rows remain
  non-authoritative.
- Codex has prior-candidate negative observations in TUI, Desktop, and exec,
  while current source still cannot use the encrypted context channel. Those
  observations do not bind the exact candidate, so its installed/live layers
  are unproven. ZCode, Hermes, and OpenClaw remain unproven.
- ADR-0118 already requires inference-owned staffing and forbids a deterministic
  offline selector. `child_delivery_evidence.py` already states that only the
  host artifact proves delivery.
- The latest recorded baseline (2026-08-11, `agency evidence latency`) covers
  200 decisions; 196 traces carry 433 receipts (~2.4 calls each). Its computed
  path reports p50 88.3 s and p95 195.9 s against the unchanged 15 s control.
  Remeasure an exact installed candidate before optimization.
- AR-242 implemented the three-success/seven-day promotion policy, but live
  native outcomes remain assignments without independently verified acceptance,
  so automatic promotion cannot fire from production work.

## exact-blocker

1. **AR-256 — canonical authority.** Publish one nine-rule/host matrix;
   reconcile stale deterministic-selection, planned-child, Job B, and status
   claims; enforce evidence-backed `done` acceptance.
2. **AR-255 — selection and evidence authority.** Remove deterministic JIT
   worker choice and fail-open compatibility selection. Carry an exact inference
   decision to spawn. Make host-written child artifacts the only green proof;
   Store `specialist_load` rows remain diagnostic.
3. **AR-180 — Codex support.** Exact-install AR-255's integrity-bound delivery
   channel and prove real children, including a multi-card child, in TUI,
   Desktop, and exec. Do not waive or downgrade Codex.
4. **AR-252 — automatic contractor critical path.** From host-backed producer
   and independent-verifier artifacts, record accepted outcomes and prove that
   three successes after the review window trigger automatic promotion. This
   P0 directly blocks AR-119.
5. **AR-253 — latency, staffing rate, and host parity.** Add the fixed
   `agency eval staffing` manifest; measure the successful recruiter decision
   separately from bounded planner/repair attempts and restore the 15 s cold
   gate; obtain current multi-card Rule-4 and automatic-promotion evidence on
   every supported host.
6. **AR-125 — value.** Run the matched Agency-on/off corpus only after valid
   candidate identity and provider contracts hold. Malformed or timed-out arms
   are invalid, never upstream losses.
7. Rule 9 cannot close until the same authority and behavior are live-proven on
   Claude, Codex, ZCode, Hermes, and OpenClaw, with unavailable hosts visibly
   unproven.

## same-task-continuity

Start the new session from this file and the repository-local founding vision,
then read AR-119, AR-255, AR-256, AR-180, AR-252, AR-253, AR-125, and ADR-0118.
Confirm `git status`, branch, HEAD, and worklog parity before editing. Preserve
unrelated work and continue from the clean substantive/ledger pair; do not
reconstruct Job B from historical text.

## next-bounded-work-package

1. Execute AR-256 phase 1 as one documentation-governance package. Starting
   from `docs/roadmap/AR-119-founding-vision.md`, create the authoritative
   rule/host evidence matrix, mark contradictions, and add both the vision-
   digest and `done`-acceptance verifiers with explicit historical exceptions
   rather than rewriting history.
2. Reconcile current north-star/session/threat statements, run documentation
   verification, and create the package's substantive/ledger pair. Then replace
   this capsule with the next bounded package; do not begin AR-255 in the same
   package.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_verify_docs_schema.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

Also run the named fast Python production spine exactly as listed in
`AGENTS.md` before the package checkpoint.

## constraints

- Codex remains a supported host; an opaque payload is an engineering blocker,
  not permission to remove support or accept weaker evidence.
- Inference is the only specialist or contractor chooser. Deterministic code may
  recall, filter hard-ineligible candidates, validate, budget, and correlate.
- Only a host-written artifact containing exact card hashes before first child
  speech proves Rule 4. Agency rows and model prose are diagnostics only.
- Keep the 15,000 ms cold control fixed. Count the single successful recruiter
  decision separately from ADR-0132's planner/recruiter repair attempts. Never
  trade authority, safety, or evidence for latency.
- Automatic promotion is on the AR-119 critical path. Do not close the umbrella
  with the production acceptance path dormant.
- Do not claim Agency superiority until a valid matched corpus proves it.
- Do not restore Job B, plan-row dispatch, work units, grants, or consumed
  receipts as the delivery transport.
- No push, PR, tracker creation/closure, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
