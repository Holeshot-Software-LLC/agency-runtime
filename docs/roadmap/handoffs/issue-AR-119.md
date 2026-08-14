---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-14
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

- **WORK ON `main` IN `C:\Workspaces\Holeshot Software\agency-runtime`.** PR #274
  merged as `be209e7a`; the `-ar119` worktree and its branch are history.
- **AR-258 is done.** All three hosts pin one runtime digest and Agency is
  globally on at generation 56. Hooks reload only in a fresh session.
- Conformance carries forward from `9724820e`; the `a25ec350` workstation run
  was 151/151. CI's quality job runs 7m33s without the matrix step, 10m35s with.
- **CI runs every matrix-cited test file** ("Run AR-119 matrix evidence"), and
  `test_release_packaging.py` derives that list from the matrix, so a new
  citation must join CI in the same commit or the contract fails.
- **`eval decision-conformance` cannot run its mutation phase here** — pytest is
  in user site-packages and the sandbox redirects `HOME`, so the baseline dies in
  58 ms. Identical on clean `main`. Run `baseline.test_nodes` with ordinary
  pytest; that proves the baseline, not the mutations.
- ADR-0159 binds exact CLI 0.147 and a pinned Desktop alpha to a sealed v3
  attestation; Sol/TUI and 65 Desktop calls omit the marker, so go unstaffed.
- No cell is proven: every Installed/Live layer is unproven, so source and
  simulation progress never promotes a cell on its own. AR-255 stays open.
- Tracker creation/sync stays pending authorization. Conformance history is in
  AR-257; exec depth-two is parked per AR-180.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix the
  sole completion authority; neither implementation nor simulation is host proof.
- AR-255 uses complete-universe inference, exact ordered multi-card v6 delivery,
  install/config/roster fences, and sealed one-use delivery proof.
- SafeClaude retains its in-lifetime collector. Codex `211563c7` preserves the
  exact CLI 0.147 profiles and adds a sealed Desktop `0.147.0-alpha.6.6` profile;
  exec depth-two/deeper stays unsupported. Census and verification runs are in
  AR-180 and the matrix; do not re-derive them here.
- Claude's earlier Rule-4 artifacts and Codex's prior negatives remain
  prior-candidate context. No exact-candidate Installed/Live proof ran.

## exact-blocker

1. **AR-180 — Codex support.** `211563c7` proves exact CLI 0.147 and Desktop
   `0.147.0-alpha.6.6` Impl/Sim. Exec depth-two is parked: no same-version
   sample, so it needs a live spawn or a drop.
2. **AR-255 — exact host proof.** Obtain explicit authorization before exact
   install or live proof. Fake-runner integration is simulation only.
3. **AR-252 — automatic contractor critical path.** The host-free half is built
   and its five acceptance items are checked. **Nothing yet collects a real
   envelope** — every producer and verifier proof is constructed by the test.
   What remains is the collector pairing one producer proof, one distinct
   verifier proof, and that verdict, then live proof on Claude and Codex.
4. **AR-253 — staffing rate, latency, and parity.** The overrun is the recruiter
   (50-85 s inference; the 9 s process floor is not the lever). Obtain
   exact-candidate evidence on all five hosts against the 15-second cold gate.
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

**Implementation and Simulation are both 45/45; Installed and Live are both
0/45, so every one of the 45 cells still reads `unproven`.** R5 Implementation
closed on a separation: process-capable and worker-creating modules are disjoint
(`agency eval spawn-authority`). AR-252's acceptance rule, recorder, and
readiness migration followed.

**What remains needs a real host: the 45 Installed and 45 Live layers, and
AR-252's envelope collector.** Claude and zcode are ready on the evidence
workstation; codex hook trust needs interactive TUI approval against digest
`3925824a5bd2`; hermes and openclaw are not on that box. The matrix cannot reach
45/45 cells from one machine.

**Start here: no activation receipt is minted for the canary's native child.**
Two live runs at `bcfbe664`; the second staffed the parent correctly
(`code-reviewer` loaded and selected, one correlated trace, zero preflight
failures) and then recorded a delegation with an empty
`retrieved_specialist_slug` and no `activation_receipt_id`, while
`native_child_delivery_verifications` stayed empty. The slug is written only when
an activation receipt is consumed, and none was minted -- the newest receipt row
predates the canary by a week, though older rows show the mechanism working with
real slugs. So it is a regression or isolated-profile gap, not an unbuilt path.
**Fix it and R4 claude Live becomes reachable with no new authorization.**
`executed_worker_kind=generic-worker` is normal; the schema requires it. The
recruiter is also nondeterministic -- run one failed at routing on the same
inputs -- so never conclude from a single canary.

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
agency eval spawn-authority --json
agency eval decision-conformance --repository . --json
git diff --check
~~~

Run focused tests, the named fast spine, and the matrix-evidence list before each
checkpoint. A checkout-local evaluator is authoritative until an exact artifact
is refreshed under explicit install authorization.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its opaque
  channel.
- Inference alone chooses specialists and contractors. Deterministic code may
  recall, filter hard-ineligible candidates, validate, budget, and correlate.
- Only a host-written artifact with exact card hashes before first child speech
  proves Rule 4. Agency rows and model prose are diagnostics.
- A plaintext-looking Codex tool argument is not proof. The authorization call
  must contain the explicit empty host marker; only exact ancestor causal calls
  may omit it under the sealed v3 profile.
- Same-process private reflection and same-account transcript plus Store forgery
  are threat-model exclusions; the lease is not protection from code already
  executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
