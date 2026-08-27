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
evidence_commit: 477c926a9b4dcad6112475f597280dca4303b66e
minimum_ledger_commit: 477c926a9b4dcad6112475f597280dca4303b66e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work only in `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never touch the shared checkout.
- Clean ledger `477c926a` binds the verified repair, exact artifacts/images,
  and Qwen1 timeout. Qwen2's sole 300-second install proves the full terminal
  graph but exposes the distinct AR-327 append-only receipt replay mismatch.
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
- AR-325 isolates the contradictory opaque failure route and the synthetic
  wrong-unit delegation left beside the real unbound worker. The repair keeps
  ordinary opaque diagnostics, preserves a fixed-unit pending dispatch,
  atomically rekeys/merges the real child, supports both callback orders and
  replay, and rejects a conflicting real dispatch.
- Five targeted cases pass. The six-file warning-strict suite passes 149/149,
  decision evaluator tests pass 17/17, and both new mutations are killed with
  source unchanged. Retained stdout hashes are `394d9276...1c4d`,
  `74a9f4f9...4141`, and `ea4477e5...3695`; all exit 0 with empty stderr.
- A separate security/atomicity slice passes 145/145 at stdout
  `ae7689e3...7a84`, exit 0, and empty stderr.
- Documentation checks pass for 893 files at `c5d005ae...18ac`; repository-wide
  Ruff/format passes at `94423e2d...0564`; diff-check output is empty. All exit 0.
- AR-326 keeps hooks live-only while admitting only one exact accepted terminal
  parent to the post-return collector. The affected 203-test suite exits 0 at
  `4e76af29...a318`; its two focused mutations are killed at
  `34858754...5cc7` with source unchanged.
- The named Python spine passes 860 tests with 3 skips at `8cda02e1...4312`.
  Full decision conformance kills 165/165 mutations at `891defed...ab8` with
  zero survived/invalid and source unchanged. Both exit 0 with empty stderr.
- Exact `4b443be2` build/Twine/verifier/six images/final verification exit 0.
  Wheel and sdist are `aaf9b461...1f7d` and `869b2842...545f`; manifest/image
  receipts are `c8fdc3f6...9c9e` and `f91c05d1...adde`.
- Qwen1 sole install `40c1c188...7f5a` exits 1 at the default 180-second Codex
  timeout, before native route/delivery/finalization. Store quick-check passes;
  correlation `5f76b443...6eaa` closes the run as `canary_failed`.
- Clean Qwen2 `9806a82a...2a2b` passes absence `1849d13e...a74c`. Its sole
  no-bypass install `ca1a6d2f...fcc1` uses the explicit 300-second window and
  exits 1 only at attestation; Codex itself exits 0 without timeout.
- Parent `01a043ab...5351`, trace `01a043ab...08c0`, child `01a043ad...4cb2`,
  route, delivery, prompt `e409b2c8...20bd`, exit-0 worker, completed run, and
  accepted finalization `38c5914f...465c` with `missing=[]` agree. Store and
  rollout hashes are `6730ee75...3195`, `aeda3b86...fa59`, `ee5d577e...005d`.
- Diagnostic `dcc4d23a...23b6` proves terminal parent/route, trusted artifact,
  decision, and receipt all resolve. Nine identity/binding fields plus nonce
  match; only digest differs: receipt `91bd1c0d...21ac` is the exact 16-record
  prefix before Codex appends `task_complete`, yielding `ee5d577e...005d`.

## exact-blocker

- Implement/checkpoint AR-327's exact receipt-bound JSONL-prefix replay, rebuild
  artifacts/images, and use one new clean Codex container; never rerun Qwen1/2.
- Claude, Hermes, OpenClaw, later ordinary processes, exact host install,
  authenticated dashboard, named gates, and final teardown remain pending.
- Cross-OS artifacts, signing, tracker parity, push/PR/merge/tag/publication,
  release, and exhaustive workflow dispatch remain unauthorized—not GO gates
  for this Linux-only bounded task unless authority changes.

## same-task-continuity

- Exact artifacts: `~/.agency-runtime/release-artifacts/`
  `dist-4b443be2f11045814250ab455d829800634c3909-linux-ar297`.
- Evidence: `~/.agency-runtime/evidence/ar297-go-19e0210b`,
  `~/.agency-runtime/evidence/ar325-callback-reconciliation-precheckpoint`, and
  `~/.agency-runtime/evidence/ar326-terminal-collector-precheckpoint`; current
  candidate evidence is `~/.agency-runtime/evidence/ar297-go-4b443be2`.
- Secret-safe helpers: `/tmp/agency-runtime-ar297-evidence.pcLOZn/`
  `run_with_litellm_key.py` and `capture_command.py`. Never print the key.
- Protected Python is `~/.agency-runtime-ci/ar297-release-0827/venv/bin/python`;
  prior UV 3.13 remains only the exact negative `pidfd` diagnostic.
- Exactly 31 containers currently carry label
  `dev.agency-runtime.proof=AR-297`; latest is
  `agency-ar297-codex-4b443be2-qwen2`. Remove all only at final teardown.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `c3493337` artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [x] Test and remove exact Gemma 3 27B; it selects the wrong role.
4. [ ] Repair/checkpoint AR-327, rebuild exact artifacts/images, then prove
   current-profile attestation in one new clean Codex install using the proven
   explicit 300-second activation window.
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
