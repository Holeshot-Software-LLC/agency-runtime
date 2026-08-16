---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-16
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
  Sol/TUI and 65 Desktop calls omit the marker, so go unstaffed.
- **CI runs every matrix-cited test file** ("Run AR-119 matrix evidence"), and
  `test_release_packaging.py` asserts that list *equals* the matrix citations,
  so a citation and a CI entry must arrive together, both directions.
- **`eval decision-conformance` cannot run its mutation phase here** (AR-257):
  the sandbox redirects `HOME` away from pytest, so the baseline dies in ~120 ms,
  identically on clean `main`. Assert every `before` snippet still matches its
  source exactly once instead.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix the
  sole completion authority; neither implementation nor simulation is host proof.
- AR-255 uses complete-universe inference, exact ordered multi-card v6 delivery,
  install/config/roster fences, and sealed one-use delivery proof. Codex
  `211563c7` preserves exact CLI 0.147 and a sealed Desktop alpha; exec
  depth-two stays unsupported and no Installed/Live proof has run on any host.
- AR-252's fourth constraint, in its issue: the verdict must bind the producer's
  *transcript* digest, unreadable to any verifier child, so Agency supplies the
  binding and the verdict is a joint object. Settle that first.

## exact-blocker

1. **AR-180 — Codex support.** `211563c7` proves exact CLI 0.147 and Desktop
   alpha Impl/Sim; exec depth-two is parked pending a live spawn or a drop.
   **AR-255:** get authorization before exact install or live proof.
2. **AR-252 — automatic contractor critical path.** The host-free half is built
   and checked, but **nothing yet collects a real envelope** — every proof is
   constructed by the test. What remains is a collector pairing one producer
   proof, one distinct verifier proof and that verdict, then live host proof.
3. **AR-253 — staffing rate, latency, and parity.** The recruiter owns the
   overrun (50-85 s; the 9 s process floor is not the lever). **Measured live
   2026-08-15: routing took 85.3 s and 124.0 s on two accepted rows, and one run
   ran 28 minutes before being marked `abandoned`.** A parent turn and its child
   usually finish before that turn's routing resolves, so the child's
   `PreToolUse` finds no `active` run to correlate, and past two terminal runs
   the 5.3.1 exactly-one-run fallback declines as well. **That, not a
   plan-boundary regression, is why the first canary returned no envelope** —
   the hook and runtime are proven working. Re-attempt after AR-253 lands or by
   holding a parent turn open past recruiter resolution.
4. **AR-125 — value.** Run the matched Agency-on/off corpus only after candidate
   and provider validity hold; malformed or timed-out arms are invalid, never
   upstream losses. Rule 9 cannot close until 1-8 are proven on all five hosts.

## same-task-continuity

After restart or compaction, load this file and `AR-119-founding-vision.md`
first, then AR-119, AR-255, AR-180, ADR-0118, ADR-0156, and ADR-0158. Confirm
branch, runtime `211563c7`, ledger `ee82c602`, status and worklog parity; do not
reconstruct retired Job B, plan-row, work-unit, grant or consumed-receipt transport.

## next-bounded-work-package

**Implementation and Simulation are both 45/45; Installed and Live are both
0/45, so every one of the 45 cells still reads `unproven`.** Claude and zcode are
ready here; codex needs the TUI trust pass against `980eb2d1b755`; hermes and
openclaw are absent, so one machine cannot reach 45.

**START HERE.** The canary completes cleanly on `76dd96b2cc50`. Parent staffing
still fails; three hypotheses refuted, see AR-253 "the three branches that remain".

1. **Claude runs `runtime-sha256-76dd96b2cc50`** at SCHEMA_VERSION 46; codex is
   behind on `530f6df6c4b6` and zcode on `980eb2d1b755`, so AR-258's one-digest
   property is broken. The packaged `agency.exe` is pinned at schema 45 and
   refuses to install — use `python -m agency_runtime.cli install --agent <host>`
   from the checkout. **A session started before an install keeps calling the old
   launcher**; the cure is a restart, never another install. Suite runs rewrite
   `current.json`; ignore it. Claude isolated-profile canaries need an explicit
   `--timeout 420`: the undeclared 120 s default kills a cold profile mid-turn.
2. **Prove Claude in two steps and do not conflate them.** First the staffing
   path: an accepted `routing_decisions` row with selected specialists and no
   preflight receipt. Only then Rule 4, which needs a host-written artifact
   carrying exact hashes for **two or more** cards before first child speech.
   Step one passing is not step two. Codex is measured the same way: the owner
   passed TUI trust 2026-08-15 but `doctor` still read
   `adapter_codex_hook_trust: unverified`; check which terminal ran it before
   assuming codex is blocked.
3. **The child judge was never shown anyone who could do the work; now it is.**
   Unproven capability had rejected **250 of 283** as
   `tool_capabilities_unproven:unknown`, `code-reviewer` included, leaving 33
   historians and narratologists, so the model correctly returned an empty list.
   `staff_native_child` now derives the parent adapter's capability receipt when
   none is supplied: **33 to 64 of 283**, `code-reviewer` eligible, every
   remaining rejection genuine. Empty now records as abstention. AR-255 proves it.
4. **Every zero-marker result on 2026-08-14 measured the schema break** — both
   canary runs, all nine host probes; both earlier readings are retracted in
   the matrix. Of 63 child artifacts under `~/.claude/projects`, 9 are marked —
   3 v5, 7 v1, **0 v6** — and `native_child_delivery_verifications` has zero
   rows, ever. One child spawned from this runtime settles v6. Owner's hands:
   a session may not call the Agent tool.

**An unrun hook and a fail-open hook look identical from outside**, so zero
Agency rows proves neither; a shim logging stdin/stdout/stderr/exit gave the
root cause on the first run. The collector names its own refusal
(`host_child_collection_reason`); `counts.specialists` / `counts.runs` are not
canary-scoped; `cd56471d` retired the delegation accounting on purpose.

## verification

**Push to `main` no longer triggers hosted CI**: direct-to-main billed a 7-10
minute run per commit, then cancelled it mid-flight on the next. Run the same
quality job locally; `gh workflow run ci.yml` still gets the Linux gate.

~~~text
python scripts/run_local_gates.py          # the gates CI ran on push (~13 min)
python scripts/run_local_gates.py --fast   # same minus the two long suites
python scripts/context_handoff_status.py --json --threshold 50
agency eval routing --json --no-details && agency eval spawn-authority --json
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
