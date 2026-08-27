---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-27
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 21051adf98231a2d74733dc34d9e7c757b861af6
minimum_ledger_commit: 21051adf98231a2d74733dc34d9e7c757b861af6
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `21051adf` binds exact AR-327 artifacts/images. Fresh Codex
  installation and attestation pass; clean Claude proof is next.
- Linux remains **NO-GO**. AR-297/#335 remain open. No tracker write, push, PR,
  merge, tag, signing, publication, release, or hosted workflow is authorized.

## completed-evidence

- Mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` hashes to
  `a4e213d6...97348`: strict assurance, additive dense recall, and every Agency
  inference route through authenticated LiteLLM aliases. No Jina route exists.
- Free Qwen 3 32B is promoted behind stable alias `task-agency-child-judge`.
  Promotion/metadata/final validation/literal/spend receipts are
  `6e19008f...1750`, `e1cba9f6...e841`, `42921a7e...867c`,
  `b686ab4b...9abe`, and `d7183bb5...2f07`. Temporary aliases are removed.
- Fresh absence `dd5b6e71...c301` exits 0. The sole no-bypass install
  `4c3e1e1b...c97e` accepts finalization `d5b3d58f...928c` with `missing=[]`.
  Parent `01a0435e...ac6f`, trace `01a0435e...aeb0`, child
  `01a0435f...02ac`, complete prompt `e409b2c8...20bd`, native delivery,
  exit-0 child, valid header, and one completed wait agree.
- Parent/child/Store hashes are `5cea5e66...3e22`, `1518a498...ecd1`, and
  `ceb65010...2fc8`; Store quick-check passes. Attestation alone fails because
  the post-return backend collector consults a live-only parent resolver.
  Content-free diagnostic `89fafc05...5b02` isolates AR-326.
- AR-325 preserves ordinary opaque diagnostics, atomically joins the fixed-unit
  dispatch to the real child in either callback order, and rejects conflicts.
  Its 149-test, 17-test, two-mutation, and 145-test receipts are
  `394d9276...1c4d`, `74a9f4f9...4141`, `ea4477e5...3695`, `ae7689e3...7a84`.
- Documentation checks pass for 893 files at `c5d005ae...18ac`; repository-wide
  Ruff/format passes at `94423e2d...0564`; diff-check output is empty. All exit 0.
- AR-326 keeps hooks live-only while admitting only one exact accepted terminal
  parent to the post-return collector. The affected 203-test suite exits 0 at
  `4e76af29...a318`; its two focused mutations are killed at
  `34858754...5cc7` with source unchanged.
- The named Python spine passes 860 tests with 3 skips at `8cda02e1...4312`.
  Full decision conformance kills 165/165 mutations at `891defed...ab8` with
  zero survived/invalid and source unchanged. Both exit 0 with empty stderr.
- Qwen1 sole install `40c1c188...7f5a` exits 1 at the default 180-second Codex
  timeout, before native route/delivery/finalization. Store quick-check passes;
  correlation `5f76b443...6eaa` closes the run as `canary_failed`.
- AR-327 reparses only the receipt-bound complete JSONL prefix. The affected
  suite passes 211 tests with 3 known AR-323 deselections at `1b0fd16d...9ab3`;
  17 decision tests pass at `f54f2441...aab`, and both mutations are killed
  with source unchanged at `527ff7d8...a78`. Focused Ruff/format passes.
- Exact Qwen2 committed-source replay `f98bb268...7cb3` exits 0: read-only and
  full restricted verification both return staffed `verified_existing_receipt`.
- Exact `7dbd0cbc` wheel/sdist are `e117b362...fc03d` and `ac30feb0...9fb6c`;
  manifest `780512b2...b7876`, six builds, and image receipt
  `00fcf8e6...5f76` exit 0. Exact image IDs are `206e94c4`, `237c788d`,
  `7869a7a3`, `91c3a5bc`, and `1b0653a5`.
- Fresh Codex `2ec2180b...17bb` passes absence `e857f524...d9bd`; its sole
  no-bypass install `54572077...ac82` exits 0 with one exact native child,
  `missing=[]`, valid header, and attestation `ded810a5...6e66`. Store/status
  correlations `ef8304ef...e30c` and `e4755e50...66a3` exit 0.

## exact-blocker

- Claude, Hermes, OpenClaw, later ordinary processes, exact host install,
  authenticated dashboard, named gates, and final teardown remain pending.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive workflow dispatch remain unauthorized—not GO gates
  for this Linux-only bounded task unless authority changes.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/`
  `dist-7dbd0cbc5cbc77e46fc795568bb63ddcf5e3ee6f-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-19e0210b`,
  `~/.agency-runtime/evidence/ar325-callback-reconciliation-precheckpoint`, and
  `~/.agency-runtime/evidence/ar326-terminal-collector-precheckpoint`; current
  candidate evidence is `~/.agency-runtime/evidence/ar297-go-7dbd0cbc`.
- Secret-safe helpers: `/tmp/agency-runtime-ar297-evidence.pcLOZn/`
  `run_with_litellm_key.py` and `capture_command.py`. Never print the key.
- Protected Python is `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`;
  prior UV 3.13 remains only the exact negative `pidfd` diagnostic.
- Exactly 32 containers currently carry label
  `dev.agency-runtime.proof=AR-297`; latest is
  `agency-ar297-codex-7dbd0cbc-ar327`. Remove all only at final teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `c3493337` artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [x] AR-327 repair/rebuild and one clean Codex install pass with verified
   current-profile attestation and no activation bypass.
5. [ ] Prove separate clean exact Claude, native-UID Hermes, and OpenClaw
   systemd production-container installs.
6. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and prompt visibility.
7. [ ] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
8. [ ] Run every named repository gate and record exact exits and hashes.
9. [ ] Update canonical issues/capsule and make each required substantive and
   `docs(worklog):` checkpoint pair.
10. [ ] Remove every container labelled `AR-297`; retain teardown evidence and
    prove zero labelled survivors.
11. [ ] Issue the Linux-scoped GO/NO-GO and complete the persistent goal only
    when every in-scope item above is truthfully closed.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Keep registration, loading, canary, delivery, Store correlation, and model
  claims distinct. Never expose or persist a secret.
- Do not configure/call Jina, overwrite foreign policy, use an activation
  bypass, or touch the shared checkout.
- All Agency inference on this system stays behind LiteLLM aliases. Any unknown
  model, endpoint, dimension, reranker, thinking level, judge route,
  harness-auth, or service-manager choice requires an owner interview.
- No tracker creation, push, PR, merge, tag, signing, publication, release,
  hosted workflow, or unrelated model/config change is authorized.
