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
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/roadmap/AR-119-acceptance-evidence.md
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
load first after any compaction or restart.

## checkpoint

- **WORK ON `main` IN `C:\Workspaces\Holeshot Software\agency-runtime`.** PR #274 merged as `be209e7a`.
- **AR-258 is done.** All three hosts pin one runtime digest and Agency is
  globally on at generation 56. Hooks reload only in a fresh session. ADR-0159
  binds exact CLI 0.147 and a pinned Desktop alpha to a sealed v3 attestation;
  Sol/TUI and 65 Desktop calls omit the marker, so go unstaffed. Conformance
  carries forward from `9724820e` (`a25ec350` was 151/151); CI's quality job
  runs 7m33s without the matrix step, 10m35s with.
- **CI runs every matrix-cited test file** ("Run AR-119 matrix evidence"), and
  `test_release_packaging.py` asserts that list *equals* the matrix citations,
  so a citation and a CI entry must arrive together, both directions.
- **`eval decision-conformance` cannot run its mutation phase here** — pytest is
  in user site-packages and the sandbox redirects `HOME`, so the baseline dies
  in 58 ms, identically on clean `main`. Run `baseline.test_nodes` with ordinary
  pytest: that proves the baseline, not the mutations. History is in AR-257.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix the
  sole completion authority; neither implementation nor simulation is host proof.
- AR-255 uses complete-universe inference, exact ordered multi-card v6 delivery,
  install/config/roster fences, and sealed one-use delivery proof; SafeClaude
  retains its in-lifetime collector. Codex `211563c7` preserves the exact CLI
  0.147 profiles and adds a sealed Desktop `0.147.0-alpha.6.6`; exec depth-two
  stays unsupported, census runs live in AR-180 and the matrix, and no
  exact-candidate Installed/Live proof has run on any host.
- AR-252's fourth constraint, in its issue: the verdict must bind the producer's
  *transcript* digest, unreadable to any verifier child, so Agency supplies the
  binding and the verdict is a joint object. Settle that first.

## exact-blocker

1. **AR-180 — Codex support.** `211563c7` proves exact CLI 0.147 and Desktop
   `0.147.0-alpha.6.6` Impl/Sim. Exec depth-two is parked: no same-version
   sample, so it needs a live spawn or a drop. **AR-255 — exact host proof:**
   obtain authorization before exact install or live proof; fake-runner
   integration is simulation only.
2. **AR-252 — automatic contractor critical path.** The host-free half is built
   and its five acceptance items are checked, but **nothing yet collects a real
   envelope** — every producer and verifier proof is constructed by the test.
   What remains is the collector pairing one producer proof, one distinct
   verifier proof, and that verdict, then live proof on Claude and Codex.
3. **AR-253 — staffing rate, latency, and parity.** The overrun is the recruiter
   (50-85 s inference; the 9 s process floor is not the lever). Obtain
   exact-candidate evidence on all five hosts against the 15-second cold gate.
4. **AR-125 — value.** Run the matched Agency-on/off corpus only after candidate
   and provider validity hold; malformed or timed-out arms are invalid, never
   upstream losses. Rule 9 is derived and cannot close until 1-8 are proven
   under one candidate on all five hosts.

## same-task-continuity

After restart or compaction, load this file and `AR-119-founding-vision.md`
first, then AR-119, AR-255, AR-180, ADR-0118, ADR-0156, and ADR-0158. Confirm
branch, runtime `211563c7`, ledger `ee82c602`, status, and worklog parity, and
do not reconstruct retired Job B, plan-row, work-unit, grant, or
consumed-receipt transport from historical sections.

## next-bounded-work-package

**Implementation and Simulation are both 45/45; Installed and Live are both
0/45, so every one of the 45 cells still reads `unproven`.** Claude and zcode
are ready here; codex hook trust needs interactive TUI approval against digest
`f0ff261120e2`; hermes and openclaw are absent, so one machine cannot reach 45.

**START HERE.** This workstation does produce readable host artifacts —
`claude -p` writes `projects/<slug>/<session>/subagents/agent-<child>.jsonl`
with exactly the record-zero shape the parser needs. That much is settled. The
rest of 2026-08-14 was spent measuring a break of our own making:

1. **A schema drift broke every hook here for two hours; it is now repaired.**
   AR-252 bumped `SCHEMA_VERSION` to 46 and checkout-local CLI runs migrated the
   live store past the pinned launcher (45), so every hook raised
   `RuntimeError: … schema is newer than this runtime (46 > 45)` and failed
   open, staffing nothing. Evidence stopped dead at **`2026-08-14T23:15:24Z`**
   across four tables; `Stop` failed *closed* — the "could not verify or persist
   the turn-scoped evidence contract" block. `agency install --all` republished
   the runtime: hooks now run **`runtime-sha256-f0ff261120e2`** at
   SCHEMA_VERSION 46, which opens the live store cleanly. **Codex hook trust is
   unverified against the new digest; owner's TUI pass, never bypass it.**
2. **Every zero-marker result on 2026-08-14 measured that break** — both canary
   runs, all nine host probes. `claude -p` runs hooks fine (a trivial hook fired
   on all five events) and the profile was never the variable; both earlier
   readings are retracted in the matrix. **Re-measure Rule 4 before trusting any
   of it.**
3. **Still true, because it is a census, not an inference:** of 63 child
   artifacts under `~/.claude/projects`, 9 are marked — 3 v5, 7 v1, **0 v6** —
   and `native_child_delivery_verifications` has zero rows, ever. Whether v6
   delivery works here is unmeasured; one child spawned from a *repaired*
   runtime settles it. Owner's hands: this session may not call the Agent tool.

**An unrun hook and a fail-open hook look identical from outside**, so zero
Agency rows proves neither. Wrap the hook command in a shim logging stdin,
stdout, stderr and exit code — that gave the root cause on the first run, after
a day of eliminating profiles and flags. The collector names its own refusal
(`host_child_collection_reason`); the recruiter is nondeterministic;
`counts.specialists` / `counts.runs` are not canary-scoped; and the delegation
columns still look like an outage after `2026-08-07T14:31Z` though `cd56471d`
retired that accounting on purpose, so **empty `retrieved_specialist_slug` /
`activation_receipt_id` proves nothing** and
`executed_worker_kind=generic-worker` is normal.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check && python scripts/verify_docs.py
python scripts/update_policy_availability.py --check && python scripts/update_worklog.py --check
python -m pytest tests/test_verify_docs_schema.py tests/test_decision_conformance.py -q -W error
ruff check agency_runtime tests scripts && ruff format --check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs && git diff --check
agency eval routing --json --no-details && agency eval spawn-authority --json
agency eval decision-conformance --repository . --json  # mutations die here; see above
~~~

Run focused tests, the fast spine, and the matrix-evidence list before each
checkpoint. A checkout-local evaluator is authoritative until an exact artifact
is refreshed under explicit install authorization.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its opaque
  channel. A plaintext-looking Codex tool argument is not proof: the
  authorization call must carry the explicit empty host marker, and only exact
  ancestor causal calls may omit it under the sealed v3 profile.
- Inference alone chooses specialists and contractors. Deterministic code may
  recall, filter hard-ineligible candidates, validate, budget, and correlate.
- Only a host-written artifact with exact card hashes before first child speech
  proves Rule 4. Agency rows and model prose are diagnostics.
- Same-process private reflection and same-account transcript plus Store forgery
  are threat-model exclusions; the lease does not protect against code already
  executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency. Automatic promotion remains on the critical path, and
  no Agency-superiority claim precedes a valid matched corpus.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
