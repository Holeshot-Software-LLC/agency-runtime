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
  - docs/roadmap/issue-AR-257-separate-decision-conformance-fixture-launcher.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
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
evidence_commit: b2e728b1facb7d770b4cf2b083ac03de3b1edfc0
minimum_ledger_commit: d1f1c6ec584ce9b1fd44e92b548d15c048e31343
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
must be loaded first after any compaction or session restart.

## checkpoint

- AR-256 and its required AR-257 gate repair are locally complete. Substantive
  commit `b2e728b1` publishes the canonical rule/host matrix, reconciles current
  doctrine and statuses, enforces completion evidence, and separates the
  decision-conformance runner from its trusted fixture launcher. Ledger commit
  `d1f1c6ec` records that package and its roadmap traceability.
- Two independent review cycles found and then verified fixes for false-green
  matrix semantics, fenced/HTML authority, hidden task markers, candidate
  ancestry, per-layer evidence laundering, and alternate-runner reuse. The
  final bounded review found no remaining Critical or High false-green path.
- Tracker creation for AR-255 through AR-257 and tracker synchronization for
  locally reopened historical issues remain pending explicit authorization.
  No missing tracker write is represented as complete.

## completed-evidence

- `AR-119-founding-vision.md` is the one wording authority;
  `AR-119-rule-host-evidence-matrix.md` is the one completion authority. The
  canonical block digest is machine-checked and the matrix binds exact candidate
  `b79a4138`, all 45 rule/host cells, and 18 asserted layer records.
- The matrix has no current `proven` top-level cell. Source negatives remain
  Rule 1 on Claude/Codex/ZCode, Rule 4 on Codex, and Rule 8 on Hermes/OpenClaw;
  exact-candidate installed/live layers remain unproven on every host.
- Claude's three Rule-4 host artifacts and Codex's TUI/Desktop/exec negatives
  are retained only as prior-candidate context. Host-neutral tests do not green
  host-specific simulation cells. Store rows remain diagnostics, never Rule-4
  proof.
- Done-status drift is fail-closed: evidence-backed historical gates are
  checked, unsupported records are reopened, and AR-161 is the sole digest- and
  provenance-bound retired exception.
- Final verification: 84 focused verifier/conformance tests passed; the named
  fast spine passed 671 with 6 skipped; dashboard UI passed 133/133; routing
  evaluation passed; decision conformance passed its baseline and killed 83/83
  mutations with zero survived/invalid and `source_unchanged=true`; docs passed
  for 684 files; full Ruff and diff checks passed.

## exact-blocker

1. **AR-255 — selection and evidence authority.** Remove deterministic JIT
   worker choice and compatibility substitution. Carry only a validated
   inference decision to a host-owned spawn, and require native host artifacts
   for delivery proof. Store projections remain diagnostic.
2. **AR-180 — Codex support.** Exact-install AR-255's integrity-bound channel
   and live-prove card-bearing, multi-card children in TUI, Desktop, and exec.
   The opaque encrypted context is a blocker, not a support waiver.
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

After compaction, load this file and `AR-119-founding-vision.md` first. Then read
AR-119, AR-255, ADR-0118, and ADR-0156 before changing runtime behavior. Confirm
branch, HEAD, status, and worklog parity. Continue from `b2e728b1` / `d1f1c6ec`;
do not reconstruct retired Job B, plan-row, work-unit, grant, or consumed-receipt
transport from historical sections.

## next-bounded-work-package

Execute AR-255 as the one next package. Replace deterministic JIT selection and
compatibility substitution with a validated inference-owned multi-card decision
that fails open unstaffed when absent or invalid. Bind decision identity, parent
and child correlation, exact card hashes, and install identity to the host-owned
delivery channel. Reject replay, stale, unbound, encrypted-but-opaque, and
Agency-authored evidence. Keep Codex supported; AR-180 owns exact installation
and live TUI/Desktop/exec proof after this implementation checkpoint.

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

Run AR-255-focused tests and the named fast Python production spine before its
checkpoint. A checkout-local evaluator is authoritative until the installed
0.1.0 CLI is refreshed under explicit install authorization.

## constraints

- Codex remains supported; never weaken evidence or parity to hide its opaque
  channel.
- Inference alone chooses specialists and contractors. Deterministic code may
  recall, filter hard-ineligible candidates, validate, budget, and correlate.
- Only a host-written artifact with exact card hashes before first child speech
  proves Rule 4. Agency rows and model prose are diagnostics.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
