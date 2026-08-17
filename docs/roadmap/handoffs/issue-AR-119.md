---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-08-17
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
branch: claude/remote-control-14de96
evidence_commit: f2f3ca88dbe4bc9adeb636a028f615c5d4886152
minimum_ledger_commit: ee82c602f2dc2d5e9632fc91b6dc071b50dc7541
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
load first after any compaction or restart.

## checkpoint

- **WORK ON `main`.** PR #275 (AR-255 P2 + hiring verdict fix) merged as `c77c67a4`.
- **All three hosts pin `2cd298158584`** (post-P2 main; AR-258 one digest
  holds). Hooks reload only in a fresh session. Matrix candidate `f2f3ca88`;
  **first Installed/Live cells ever: R2 R3 R6 R7 proven at all four layers on
  claude, R5 Installed proven** — see AR-119-c77c67a4-live-evidence.md.
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
branch, candidate `f2f3ca88`, runtime `2cd298158584`, worklog parity; do not
reconstruct retired Job B, plan-row, work-unit, grant or consumed-receipt transport.

## next-bounded-work-package

**Installed is 5/45 and Live 4/45 — green for the first time: R2 R3 R6 R7
proven at all four layers on claude plus R5 Installed, bound to candidate
`f2f3ca88` / runtime `2cd298158584`.** Codex activation failed 2/2 under the
authorized bypass; zcode has no CLI here; hermes and openclaw stay absent.

**THE BLOCKER MOVED.** The child judge declines **on the merits**: the post-P2
series split legacy / legacy / `native_child_abstention_confirmed` (n=3).

1. **The judge was RIGHT — and the owner has RULED.** The re-measured v3
   series proved the chain twice (routing accepted, card loaded, EXACTLY
   one child, capture == work unit) with the pure unit declined both
   times, once repair-confirmed (`0165dff0`). The owner lowered the
   threshold (2026-08-17): small units still get cards. Policy shipped in
   the complete-universe judge prompt — task size is a non-reason,
   coverage the only decline ground, abstention escape kept. Next: merge,
   reinstall, one claude canary; acceptance is the child STAFFING and
   `native_child_delivery_verifications` gaining its first row ever.
2. **The AR-253 overrun has a harder edge.** A 486 s+ recruiter draw outlived
   the claude hook window: the host cancelled the hook (`hook_cancelled` in
   session `2b4b19d4`), the turn proceeded unstaffed and answered, and the
   store got a run row with ZERO receipts — a cancelled hook is a third
   sibling of unrun-vs-fail-open, visible only in the host artifact. Accepted
   routing draws tonight ran 88.6–283.2 s; the cancelled one exceeded 486 s.
   R8's candidate artifact is that session; recorded, deliberately unclaimed.
3. **Sixteen child decisions, zero staffed** — 13 abstained (`task_chars` 541
   to 3,431, `code-reviewer` always offered), 1 unavailable, 2 invalid. Size
   and universe stay excluded; the merits reading stands. Rule 6 keeps firing
   live: `function-naming-advisor` and `contractor-reuse-system-analyst` were
   both minted organically tonight and the first was reused with no re-hire.
   A six-child parent still cannot prove Rule 4 (`multiple_child_artifacts`).
4. **The v6 census is unchanged — zero envelopes ever** and
   `native_child_delivery_verifications` has zero rows: consistent with a
   judge that has never accepted, not with a delivery fault. Codex bypass
   runs DID write receipts (first codex rows since 08-14); the failing stage
   is the shared recruiter, not codex wiring — attended TUI trust and a real
   codex turn are the owner's path. zcode activation needs his own session.
   Canaries still need `--timeout 420`; sessions predating installs are stale.

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
