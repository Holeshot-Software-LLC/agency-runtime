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
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
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
evidence_commit: 7e1b3603e69d04531d9d606fa8f5501946e89fb1
minimum_ledger_commit: fb650b04c26d82f406621808f1cbb0f36c6256ec
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Current bootstrap projection for completing the owner-confirmed nine-rule
vision. The canonical issue retains history; this file and the founding vision
must be loaded first after any compaction or session restart.

## checkpoint

- The current clean recovery pair is AR-255 runtime `7e1b3603` and ledger
  `fb650b04` on `codex/ar119-vision-mitigation-handoff`.
- AR-255 is still open. Its first five acceptance gates are checkpointed;
  Codex's integrity-bound child channel and exact-candidate Claude
  Installed/Live proof remain open.
- Matrix candidate `7e1b3603` has no proven top-level cell. Rule 1 source and
  simulation are repaired on all five adapters; Claude Rule 4 source and
  simulation are proven; Codex Rule 4 remains negative. Every Installed and
  Live layer remains unproven.
- Tracker creation for AR-255 through AR-257 and tracker synchronization for
  locally reopened historical issues remain pending explicit authorization.
  No missing tracker write is represented as complete.

## completed-evidence

- `AR-119-founding-vision.md` is the sole wording authority and the matrix is
  the sole completion authority. Candidate `7e1b3603` preserves all 45 cells
  without converting implementation or simulation into host proof.
- AR-255 now uses complete-universe inference, exact ordered multi-card v6
  delivery, install/config/roster fences, fail-open diagnostics, and sealed
  one-use delivery proof. Store-only state and caller mappings are diagnostic.
- SafeClaude allocates a live private lease, brackets the real process with a
  one-use invocation window, and collects one canonical current artifact before
  profile cleanup. Codex 0.147 remains unstaffed with
  `unsupported_opaque_interagent_channel`.
- Final focused verification passed 229 tests with 1 skipped. The named fast
  Python spine passed 673 with 6 skipped; dashboard UI passed 134; docs passed
  for 685 Markdown files. Full Ruff lint/format, metadata, policy, worklog, and
  whitespace checks passed.
- Checkout routing evaluation passed every gate. Decision conformance passed
  its baseline, killed 83/83 mutations with zero survived or invalid, and
  reported `source_unchanged=true`.
- Two independent adversarial passes drove origin, capability, install-home,
  caller-root, and replay repairs. The final reattack found no unresolved
  Critical or High issue; its child-evidence suite passed 54 tests.
- Claude's three earlier Rule-4 artifacts and Codex's earlier TUI/Desktop/exec
  negatives remain prior-candidate context. No real Claude or Codex executable
  was invoked for this checkpoint, so every Installed and Live layer is still
  unproven.

## exact-blocker

1. **AR-180 — Codex support.** Codex 0.147 exposes no plaintext or authenticated
   initial inter-agent assignment before first child speech. Keep the host
   supported and fail open unstaffed until Codex exposes that boundary; AR-180
   exact-installs and live-proves it in TUI, Desktop, and exec when available.
2. **AR-255 — exact host proof.** Build and verify candidate `7e1b3603`, then
   obtain one current Claude artifact through the real executable. The passing
   fake-runner integration is simulation, not Installed or Live authority.
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
Confirm branch, runtime `7e1b3603`, ledger `fb650b04`, status, and worklog
parity. Do not reconstruct retired Job B, plan-row, work-unit, grant, or
consumed-receipt transport from historical sections.

## next-bounded-work-package

Start AR-180 with a read-only exact-host capability preflight: identify the
current Codex executable/version and determine whether any authenticated
pre-speech child assignment is available. Keep Codex unstaffed while the
channel is opaque. An exact candidate build, install, trust change, or live
Claude/Codex canary requires explicit authorization. If authorized and the
channel exists, verify/install `7e1b3603`, obtain one real Claude artifact, and
run bounded Codex TUI, Desktop, and exec proof. Then continue AR-252, AR-253,
AR-125, and derived Rule 9 in dependency order.

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
- Same-process private reflection and same-account transcript plus Store
  forgery are threat-model exclusions; do not describe the lease as protection
  from code already executing as the owner inside Agency.
- Keep the 15,000 ms cold control fixed; do not trade authority, safety, or
  evidence for latency.
- Automatic promotion remains on the AR-119 critical path.
- Do not claim Agency superiority before a valid matched corpus proves it.
- No push, PR, tracker write, hosted dispatch, install, trust action,
  publication, tag, release, or repository-setting change without authorization.
