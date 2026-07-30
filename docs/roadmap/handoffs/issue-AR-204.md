---
title: "AR-204 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, product, dashboard, inference, activation, automation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-204
branch: codex/ar-203-readme-story-final-proof
evidence_commit: c387b6503813b7d34120f2406f9e8fdd965edd6d
minimum_ledger_commit: ecfb24126d5f359cd6bc02070906bc9f73a21aef
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189
---

# AR-204 active recovery capsule

Bounded recovery projection for making the README product story executable.
The [canonical issue](../issue-AR-204-reconcile-readme-story-contract.md) owns
acceptance; this file records only current proof and the next package.

## checkpoint

- The active goal remains `README's main story works in reality.`
- The owner resolved all nine product ambiguities on 2026-07-30.
- Commit `c387b65` makes README and ADR-0117 through ADR-0119 state the
  locked target contract.
- Tracker [#189](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189)
  records AR-204 under `epic:product`.
- No implementation change or new live canary has run in this package yet.
- Exact installed build `5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748`
  remains the last live-tested build and is not accepted as product proof.

## completed-evidence

- Production currently has complete tested dashboard mutation handlers and CLI
  writers behind blanket unavailable/read-only gates.
- `dashboard service open` currently enters the retired presence verifier even
  though its handler may install, repair, start, or restart an owned service.
- The deterministic architecture-anchor helper reported by the owner is absent
  from current source, but ADR-0088 and offline fallback behavior still permit
  deterministic specialist selection.
- Codex registration and native trust inventory do not prove hook start, route,
  specialist injection, delegation, or finalization.
- The owner explicitly authorized Codex's supported hook-trust bypass for this
  session. Bypassed evidence must never be labeled trusted.

## exact-blocker

The documentation contract is frozen, but current production code still
violates it at owner authority, offline staffing, native activation propagation,
response correction, and dashboard usability boundaries.

## same-task-continuity

Continue in this task through bounded implementation packages. Do not dispatch
hosted Actions while GitHub spending limits prevent runner execution. Preserve
the owner-untracked analysis draft and `uv.lock`.

## next-bounded-work-package

1. Remove the retired human-presence dispatch gate from normal owner CLI and
   dashboard service operations.
2. Restore owner dashboard configuration/control clients and allow owner bearer
   mutations while keeping broker credentials read-only.
3. Run focused CLI, dashboard server, and dashboard UI tests.
4. Update this capsule and checkpoint before beginning inference-only staffing.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py --allow-open-complete
git diff --check
~~~

## constraints

- Dashboard and CLI parity covers supported configuration and runtime/governance
  controls, not developer-only test or evaluation commands.
- The dashboard bearer remains automatic loopback request isolation.
- Deterministic code may recall and verify but never select a specialist.
- Missing/invalid inference and malformed/corrected headers fail loudly.
- Use the supported Codex autonomous trust bypass when needed; never edit
  undocumented private trust state or claim bypassed hooks are trusted.
- One live product trial per exact installed build; correction count must be
  exactly zero.
